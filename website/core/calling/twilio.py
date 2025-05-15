import os
import uuid

from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.timezone import now
from django.core.files import File

from twilio.twiml.voice_response import VoiceResponse, Dial
from twilio.request_validator import RequestValidator
from twilio.rest import Client

from core.models import Lead, LeadNote, Message, User
from core.utils import cleanup_dir_files, download_file_from_twilio
from website import settings
from communication.forms import OutboundPhoneCallForm
from .base import CallingServiceInterface

from communication.enums import TwilioWebhookCallbacks, TwilioWebhookEvents
from core.messaging.utils import strip_country_code
from core.models import PhoneCall, PhoneCallTranscription
from core.messaging import messaging_service

class TwilioCallingService(CallingServiceInterface):
    def __init__(self, account_sid, auth_token, transcription_service, ai_agent):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.transcription_service = transcription_service
        self.ai_agent = ai_agent
        self.client = Client(account_sid, auth_token)
        self.validator = RequestValidator(auth_token)

    def handle_inbound_call(self, request) -> HttpResponse:
        response = VoiceResponse()

        if request.method != "POST":
            return HttpResponse("Only POST allowed", status=405)
        
        if not settings.DEBUG:
            valid = self.validator.validate(
                request.build_absolute_uri(),
                request.POST,
                request.META.get("HTTP_X_TWILIO_SIGNATURE", "")
            )

            if not valid:
                return HttpResponse("Invalid Twilio signature.", status=403)

        form = request.POST

        call_sid = form.get("CallSid")
        call_from = form.get("From")
        call_to = form.get("To")
        call_status = form.get("CallStatus")

        if not all([call_sid, call_from, call_to, call_status]):
            return HttpResponse("Missing required fields", status=400)

        from_number = strip_country_code(call_from)
        to_number = strip_country_code(call_to)

        forward = User.objects.filter(phone_number=to_number).first()
        if not forward:
            return HttpResponse("No matching phone number found", status=404)

        forward_number = forward.forward_phone_number

        recording_callback_url = TwilioWebhookCallbacks.get_full_url(TwilioWebhookCallbacks.RECORDING.value)
        action_url = TwilioWebhookCallbacks.get_full_url(TwilioWebhookCallbacks.STATUS.value)

        try:
            dial = Dial(
                record='record-from-ringing-dual',
                recording_status_callback=recording_callback_url,
                recording_status_callback_event="completed",
                status_callback_event=TwilioWebhookEvents.all(),
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
            return HttpResponse("An unexpected error occurred.", status=500)

    def handle_call_status_callback(self, request) -> HttpResponse:
        if request.method != "POST":
            return HttpResponse("Only POST requests are allowed", status=405)
        
        if not settings.DEBUG:
            valid = self.validator.validate(
                request.build_absolute_uri(),
                request.POST,
                request.META.get("HTTP_X_TWILIO_SIGNATURE", "")
            )

            if not valid:
                return HttpResponse("Invalid Twilio signature.", status=403)

        call_sid = request.POST.get("CallSid")
        dial_status = request.POST.get("DialCallStatus")
        dial_duration = request.POST.get("DialCallDuration", "0")

        if not call_sid:
            return HttpResponse("Missing CallSid", status=400)

        try:
            phone_call = PhoneCall.objects.get(external_id=call_sid)

            phone_call.call_duration = int(dial_duration)
            phone_call.status = dial_status
            phone_call.save()

            lead_phone_number = phone_call.call_from
            outbound_calls = PhoneCall.objects.filter(call_to=lead_phone_number).count()
            inbound_calls = PhoneCall.objects.filter(call_from=lead_phone_number).count()

            is_first_call = inbound_calls + outbound_calls == 1
            MISSED_STATUSES = {"busy", "failed", "no-answer"}

            if phone_call.is_inbound and is_first_call and dial_status in MISSED_STATUSES:
                user = User.objects.filter(phone_number=phone_call.call_to).first()

                if not user:
                    return HttpResponse('User not found', status=500)

                language_note = " Please write the message in Spanish." if user.username == "yova" else ""

                prompt = (
                    f"A new lead just called but we missed it. "
                    "Send a friendly text saying we're sorry we missed their call "
                    "and that someone will be in touch shortly. "
                    "Here's an example: "
                    f"Hi! This is {user.first_name} with YD Cocktails, sorry we missed your call. We'll get back to you shortly."
                    + language_note
                )

                try:
                    text = self.ai_agent.generate_response(prompt=prompt)

                    message = Message(
                        text=text,
                        text_from=phone_call.call_to,
                        text_to=phone_call.call_from,
                        is_inbound=False,
                        status='pending',
                        is_read=True
                    )

                    resp = messaging_service.send_text_message(message=message)

                    message.external_id = resp.sid
                    message.status = resp.status
                    message.save()
                except BaseException as e:
                    return HttpResponse('Error while generating response from AI Agent', status=500)

            elif not phone_call.is_inbound and is_first_call and dial_status in MISSED_STATUSES:
                user = User.objects.filter(phone_number=phone_call.call_from).first()

                if not user:
                    return HttpResponse('User not found', status=500)

                language_note = " Please write the message in Spanish." if user.username == "yova" else ""

                prompt = (
                    "A new lead just came in, I tried to call them but they missed it. "
                    "Send a friendly text saying we received their bartending inquiry and letting them know they're free to call back at their earliest convenience."
                    "Follow the example shown below exactly, do not add any extra text. And swap the first name with the correct value."
                    f"Hi! This is {user.first_name} with YD Cocktails, we just tried giving you a call about your bartending inquiry but couldn't connect."
                    + language_note
                )

                try:
                    text = self.ai_agent.generate_response(prompt=prompt)

                    message = Message(
                        text=text,
                        text_from=phone_call.call_from,
                        text_to=phone_call.call_to,
                        is_inbound=True,
                        status='pending',
                        is_read=True
                    )

                    resp = messaging_service.send_text_message(message=message)

                    message.external_id = resp.sid
                    message.status = resp.status
                    message.save()
                except Exception as e:
                    return HttpResponse('Error while generating response from AI Agent', status=500)

            return HttpResponse('Success!', status=200)

        except PhoneCall.DoesNotExist:
            return HttpResponse("Call not found", status=404)

    def handle_call_recording_callback(self, request) -> HttpResponse:
        if request.method != "POST":
            return HttpResponse("Only POST requests are allowed", status=405)
        
        if not settings.DEBUG:
            valid = self.validator.validate(
                request.build_absolute_uri(),
                request.POST,
                request.META.get("HTTP_X_TWILIO_SIGNATURE", "")
            )

            if not valid:
                return HttpResponse("Invalid Twilio signature.", status=403)

        call_sid = request.POST.get("CallSid")
        recording_sid = request.POST.get("RecordingSid")

        if not call_sid or not recording_sid:
            return HttpResponse("Missing CallSid or RecordingSid", status=400)

        recording_url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.account_sid}/Recordings/{recording_sid}.mp3?RequestedChannels=2"
        )

        try:
            phone_call = PhoneCall.objects.get(external_id=call_sid)
            phone_call.recording_url = recording_url
            phone_call.save()

            if phone_call.status != "completed":
                return HttpResponse("Success!", status=200)

            job_name = str(uuid.uuid4())
            audio_filename = job_name + ".mp3"

            local_audio_path = os.path.join(settings.UPLOADS_URL, audio_filename)

            download_file_from_twilio(phone_call.recording_url, local_audio_path)

            with open(local_audio_path, 'rb') as audio:
                transcription = PhoneCallTranscription(
                    phone_call=phone_call,
                    external_id=job_name,
                )
                transcription.audio.save(audio_filename, File(audio), save=False)

            self.transcription_service.transcribe_audio(transcription=transcription)

            self._delete_call_recording(recording_sid)

            user_phone = phone_call.call_to if phone_call.is_inbound else phone_call.call_from
            user = User.objects.filter(phone_number=user_phone).first()

            lead_phone = phone_call.call_from if phone_call.is_inbound else phone_call.call_to
            lead = Lead.objects.filter(phone_number=lead_phone).first()

            if lead is not None:
                note = self.ai_agent.summarize_phone_call(transcription.text)

                LeadNote.objects.create(
                    note=note,
                    lead=lead,
                    user=user,
                )
        
            return HttpResponse("Success!", status=200)

        except PhoneCall.DoesNotExist:
            return HttpResponse("Phone call not found", status=404)

        except Exception as e:
            return HttpResponse("Internal server error", status=500)
        
        finally:
            cleanup_dir_files(settings.UPLOADS_URL)
    
    def _delete_call_recording(self, recording_sid: str) -> None:
        try:
            self.client.recordings(recording_sid).delete()
        except BaseException as e:
            raise RuntimeError(f"Failed to delete recording: {e}")
    
    def handle_outbound_call(self, from_: str, to_: str):
        recording_callback_url = TwilioWebhookCallbacks.get_full_url(TwilioWebhookCallbacks.RECORDING.value)
        status_callback_url = TwilioWebhookCallbacks.get_full_url(TwilioWebhookCallbacks.STATUS.value)

        response = VoiceResponse()
        try:
            dial = Dial(
                record='record-from-ringing-dual',
                recording_status_callback=recording_callback_url,
                recording_status_callback_event="completed",
                status_callback=status_callback_url,
                status_callback_event=TwilioWebhookEvents.all(),
                action=status_callback_url
            )
            dial.number(to_)
            response.append(dial)

            call = self.client.calls.create(
                from_=from_,
                to=to_,
                twiml=str(response)
            )

            PhoneCall.objects.create(
                external_id=call.sid,
                call_duration=0,
                date_created=now(),
                call_from=from_,
                call_to=to_,
                is_inbound=False,
                recording_url="",
                status=call.status,
            )

        except Exception as e:
            raise Exception('Error handling outbound call.')