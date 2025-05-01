import os
import uuid
import requests
from abc import ABC, abstractmethod

from django.http import HttpResponse, HttpResponseBadRequest, HttpRequest
from django.utils.timezone import now
from django.core.files import File

from twilio.twiml.voice_response import VoiceResponse, Dial

from core.models import User
from website import settings

from .enums import TwilioWebhookCallbacks, TwilioWebhookEvents
from .utils import strip_country_code
from .models import PhoneCall, PhoneCallTranscription

class CallingServiceInterface(ABC):
    @abstractmethod
    def handle_inbound_call(self, request: HttpRequest) -> HttpResponse:
        pass

    @abstractmethod
    def handle_call_status(self, request: HttpRequest) -> HttpResponse:
        pass

    @abstractmethod
    def handle_call_recording_callback(
        self, request: HttpRequest, transcription_service: TranscriptionServiceInterface
    ) -> HttpResponse:
        pass

class TwilioCallingService(CallingServiceInterface):
    def __init__(self, account_sid: str, auth_token: str, transcription_service: TranscriptionServiceInterface):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.transcription_service = transcription_service

    def handle_inbound_call(self, request: HttpRequest) -> HttpResponse:
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

    def handle_call_recording_callback(self, request: HttpRequest) -> HttpResponse:
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

            recording_sid = TwilioService.extract_recording_sid(phone_call.recording_url)
            TwilioService.delete_recording(recording_sid)
            TranscriptionService.summarize(phone_call, transcript_text)

            AttachmentService.cleanup_local_files(settings.UPLOADS_URL)

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


class CallingServiceFactory:
    @staticmethod
    def get_service() -> TwilioCallingService:
        if settings.DEBUG:
            return CallingServiceFactory._create_twilio_service()
        return CallingServiceFactory._create_twilio_service()

    @staticmethod
    def _create_twilio_service() -> TwilioCallingService:
        transcription_service = TranscriptionServiceFactory.get_service()
        return TwilioCallingService(
            account_sid=settings.TWILIO_ACCOUNT_SID,
            auth_token=settings.TWILIO_AUTH_TOKEN,
            transcription_service=transcription_service,
        )

class CallingService(CallingServiceInterface):
    def __init__(self):
        self.service = CallingServiceFactory.get_service()

    def handle_inbound_call(self, request: HttpRequest) -> HttpResponse:
        return self.service.handle_inbound_call(request)

    def handle_call_status(self, request: HttpRequest) -> HttpResponse:
        return self.service.handle_call_status(request)

    def handle_call_recording_callback(self, request: HttpRequest) -> HttpResponse:
        return self.service.handle_call_recording_callback(request)