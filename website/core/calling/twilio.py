import os
import re
import uuid
import requests

from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.timezone import now
from django.core.files import File

from twilio.twiml.voice_response import VoiceResponse, Dial
from twilio.rest import Client

from core.models import Lead, User
from core.utils import cleanup_dir_files
from website import settings
from core.agent import AIAgent
from .base import CallingServiceInterface

from communication.transcription import TranscriptionService, TranscriptionServiceFactory
from communication.enums import TwilioWebhookCallbacks, TwilioWebhookEvents
from core.messaging.utils import strip_country_code
from core.models import PhoneCall, PhoneCallTranscription

class TwilioCallingService(CallingServiceInterface):
    def __init__(self, account_sid, auth_token, transcription_service, ai_agent):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.transcription_service = transcription_service
        self.ai_agent = ai_agent
        self.client = Client(account_sid, auth_token)

    def handle_inbound_call(self, request) -> HttpResponse:
        if request.method != "POST":
            response = VoiceResponse()
            response.say("Only POST allowed")
            return HttpResponse(str(response), content_type="application/xml", status=405)

        response = VoiceResponse()

        form = request.POST
        call_sid = form.get("CallSid")
        call_from = form.get("From")
        call_to = form.get("To")
        call_status = form.get("CallStatus")

        if not all([call_sid, call_from, call_to, call_status]):
            response.say("Missing required fields")
            return HttpResponseBadRequest(str(response), content_type="application/xml")

        from_number = strip_country_code(call_from)
        to_number = strip_country_code(call_to)

        forward = User.objects.filter(phone_number=to_number).first()
        if not forward:
            response.say("No matching phone number found")
            return HttpResponse(str(response), content_type="application/xml", status=404)

        forward_number = forward.phone_number
        recording_callback_url = TwilioWebhookCallbacks.get_full_url(TwilioWebhookCallbacks.INBOUND.value)
        action_url = TwilioWebhookCallbacks.get_full_url(TwilioWebhookCallbacks.STATUS.value)

        try:
            dial = Dial(
                record="true",
                recording_status_callback=recording_callback_url,
                recording_status_callback_event=TwilioWebhookEvents.all(),
                action=action_url
            )
            dial.number(forward_number)
            response.append(dial)

            PhoneCall.objects.create(
                external_id=call_sid,
                call_duration=0,
                date_created=now(),
                call_from=from_number,
                call_to=to_number,
                is_inbound=True,
                recording_url="",
                status=call_status,
            )

            return HttpResponse(str(response), content_type="application/xml", status=200)

        except Exception as e:
            print(f"Server error: {e}")
            response.say("An unexpected error occurred.")
            return HttpResponse(str(response), content_type="application/xml", status=500)
        
    def handle_inbound_call_end(self, request) -> HttpResponse:
        response = VoiceResponse()

        if request.method != "POST":
            response.say("Only POST requests are allowed")
            return HttpResponse(str(response), content_type="application/xml", status=405)

        call_sid = request.POST.get("CallSid")
        dial_status = request.POST.get("DialCallStatus")
        dial_duration = request.POST.get("DialCallDuration", "0")

        if not call_sid:
            response.say("Missing CallSid")
            return HttpResponse(str(response), content_type="application/xml", status=400)

        try:
            phone_call = PhoneCall.objects.get(external_id=call_sid)

            phone_call.call_duration = int(dial_duration)
            phone_call.status = dial_status
            phone_call.save()

            MISSED_STATUSES = {"busy", "failed", "no-answer"}
            if phone_call.is_inbound and dial_status in MISSED_STATUSES:
                print("Initiate missed inbound call text")
            elif not phone_call.is_inbound and dial_status in MISSED_STATUSES:
                print("Initiate missed outbound call text")

            return HttpResponse(str(response), content_type="application/xml", status=200)

        except PhoneCall.DoesNotExist:
            response.say("Phone call not found")
            return HttpResponse(str(response), content_type="application/xml", status=404)

        except Exception as e:
            response.say("Internal server error")
            print(f"Error during inbound call end: {e}")
            return HttpResponse(str(response), content_type="application/xml", status=500)

    def handle_call_recording_callback(self, request) -> HttpResponse:
        response = VoiceResponse()

        if request.method != "POST":
            response.say("Only POST requests are allowed")
            return HttpResponse(str(response), content_type="application/xml", status=405)

        call_sid = request.POST.get("CallSid")
        recording_sid = request.POST.get("RecordingSid")

        if not call_sid or not recording_sid:
            response.say("Missing CallSid or RecordingSid")
            return HttpResponse(str(response), content_type="application/xml", status=400)

        recording_url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.account_sid}/Recordings/{recording_sid}.mp3?RequestedChannels=2"
        )

        try:
            phone_call = PhoneCall.objects.get(external_id=call_sid)
            phone_call.recording_url = recording_url
            phone_call.save()

            job_name = uuid.uuid4()
            audio_filename = job_name + ".mp3"

            local_audio_path = os.path.join(settings.UPLOADS_URL, audio_filename)

            self._download_file_from_url(phone_call.recording_url, local_audio_path)

            with open(local_audio_path, 'rb') as audio:
                transcription = PhoneCallTranscription(
                    phone_call=phone_call,
                    external_id=job_name,
                )
                transcription.audio.save(audio_filename, File(audio), save=False)

            self.transcription_service.transcribe_audio(transcription=transcription)

            recording_sid = self._extract_recording_sid(phone_call.recording_url)
            self._delete_call_recording(recording_sid)

            user_phone = phone_call.call_to if phone_call.is_inbound else phone_call.call_from
            user = User.objects.filter(phone_number=user_phone).first()

            lead_phone = phone_call.call_from if phone_call.is_inbound else phone_call.call_to
            lead = Lead.objects.filter(phone_number=lead_phone).first()

            if lead is not None:
                self.ai_agent.summarize(lead.lead_id, user.user_id, transcription.text)

            cleanup_dir_files(settings.UPLOADS_URL)

            return HttpResponse(str(response), content_type="application/xml", status=200)

        except PhoneCall.DoesNotExist:
            response.say("Phone call not found")
            return HttpResponse(str(response), content_type="application/xml", status=404)

        except Exception as e:
            response.say("Internal server error")
            print(f"Error during recording callback: {e}")
            return HttpResponse(str(response), content_type="application/xml", status=500)
    
    def _download_file_from_twilio(self, twilio_recording_url: str, local_file_path: str) -> None:
        try:
            response = requests.get(
                twilio_recording_url,
                auth=(self.account_sid, self.auth_token),
                stream=True
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise Exception(f"Failed to download file: {e}")

        try:
            with open(local_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"File downloaded successfully: {local_file_path}")
        except Exception as e:
            raise Exception(f"Failed to save file locally: {e}")
    
    def _extract_recording_sid(self, recording_url: str) -> str:
        """
        Extracts the recording SID from a Twilio recording URL.

        Example:
        https://api.twilio.com/2010-04-01/Accounts/ACxxx/Recordings/RE1234567890abcdef.mp3
        -> returns: RE1234567890abcdef
        """
        match = re.search(r'/Recordings/([A-Z0-9]+)\.mp3', recording_url)
        if not match:
            raise ValueError(f"Could not extract recording SID from URL: {recording_url}")
        return match.group(1)
    
    def _delete_call_recording(self, recording_sid: str) -> None:
        try:
            self.client.recordings(recording_sid).delete()
            print("Recording deleted successfully")
        except BaseException as e:
            raise RuntimeError(f"Failed to delete recording: {e}")