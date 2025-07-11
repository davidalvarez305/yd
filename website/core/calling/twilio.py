import os
import uuid

from django.http import HttpResponse
from django.utils.timezone import now
from django.core.files import File

from twilio.twiml.voice_response import VoiceResponse, Dial
from twilio.request_validator import RequestValidator
from twilio.rest import Client

from core.models import CallTrackingNumber, Lead, LeadNote, Message, PhoneCallStatusHistory, User
from core.utils import cleanup_dir_files, download_file_from_twilio
from website import settings
from core.logger import logger
from .base import CallingServiceInterface

from communication.enums import TwilioWebhookCallbacks, TwilioWebhookEvents
from core.messaging.utils import strip_country_code
from core.models import PhoneCall, PhoneCallTranscription
from core.messaging import messaging_service

MISSED_STATUSES = {"busy", "failed", "no-answer"}

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

        forward = CallTrackingNumber.objects.filter(phone_number=to_number).first()
        if not forward:
            return HttpResponse("No matching phone number found", status=400)

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
            logger.error(e, exc_info=True)
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
            phone_call.save(update_fields=['call_duration', 'status'])

            user_phone = phone_call.call_to if phone_call.is_inbound else phone_call.call_from
            user = User.objects.filter(phone_number=user_phone).first()

            if phone_call.status in MISSED_STATUSES:
                self.handle_missed_call(phone_call=phone_call, ctx={ 'user': user })

        except Exception as e:
            logger.error(e, exc_info=True)
            return HttpResponse("Call not found", status=500)
        
        return HttpResponse('Success!', status=200)

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

        recording_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Recordings/{recording_sid}.mp3?RequestedChannels=2"

        try:
            phone_call = PhoneCall.objects.get(external_id=call_sid)
            phone_call.recording_url = recording_url
            phone_call.save()

            if phone_call.status != "completed" or phone_call.call_duration < 30:
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
                ctx = { 'lead': lead, 'transcription': transcription, 'user': user }
                note = self.ai_agent.summarize_phone_call(ctx=ctx)

                LeadNote.objects.create(
                    note=note,
                    lead=lead,
                    user=user,
                )
        
            return HttpResponse("Success!", status=200)

        except Exception as e:
            logger.error(e, exc_info=True)
            return HttpResponse("Internal server error", status=500)
        
        finally:
            cleanup_dir_files(settings.UPLOADS_URL)
    
    def _delete_call_recording(self, recording_sid: str) -> None:
        try:
            self.client.recordings(recording_sid).delete()
        except BaseException as e:
            raise RuntimeError(f"Failed to delete recording: {e}")
    
    def handle_outbound_call(self, ctx: dict):
        user_phone_number = ctx.get('user_phone_number')
        client_phone_number = ctx.get('client_phone_number')
        company_phone_number = ctx.get('company_phone_number')

        if None in [user_phone_number, client_phone_number, company_phone_number]:
            raise ValueError('Missing context in request.')

        try:
            recording_callback_url = TwilioWebhookCallbacks.get_full_url(
                TwilioWebhookCallbacks.RECORDING.value
            )
            status_callback_url = TwilioWebhookCallbacks.get_full_url(
                TwilioWebhookCallbacks.OUTBOUND_STATUS.value
            )

            response = VoiceResponse()
            
            dial = Dial(
                caller_id=company_phone_number,
            )

            dial.number(
                client_phone_number,
                status_callback=status_callback_url,
                status_callback_method='POST',
                status_callback_event=TwilioWebhookEvents.outbound(),
                recording_status_callback=recording_callback_url,
                recording_status_callback_event="completed"
            )
            response.append(dial)

            self.client.calls.create(
                from_=company_phone_number,
                to=user_phone_number,
                twiml=str(response)
            )

        except Exception as e:
            logger.error(e, exc_info=True)
            raise Exception('Error handling outbound call.')
    
    def handle_outbound_call_status_callback(self, request) -> HttpResponse:
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

        child_call_sid = request.POST.get('DialCallSid')
        call_sid = child_call_sid if child_call_sid else request.POST.get("CallSid")
        call_status = request.POST.get("CallStatus")
        call_duration = int(request.POST.get("CallDuration", "0"))
        call_from = request.POST.get("From")
        call_to = request.POST.get("To")

        if not call_sid:
            return HttpResponse("CallSid is missing.", status=400)

        phone_call, created = PhoneCall.objects.get_or_create(
            external_id=call_sid,
            defaults={
                "call_from": strip_country_code(call_from),
                "call_to": strip_country_code(call_to),
                "call_duration": call_duration,
                "date_created": now(),
                "is_inbound": False,
                "status": call_status,
            }
        )

        if not created:
            phone_call.call_duration = call_duration
            phone_call.status = call_status
            phone_call.save(update_fields=['call_duration', 'status'])

        if phone_call.status == 'completed' and phone_call.status not in MISSED_STATUSES:
            # Check if child call was ever answered
            was_answered = PhoneCallStatusHistory.objects.filter(phone_call=phone_call, status='answered').exists()
            if not was_answered:
                phone_call.status = 'missed'
                phone_call.save(update_fields=['status'])
        
        if phone_call.status in phone_call.status in MISSED_STATUSES:
            try:
                user = User.objects.get(phone_number=phone_call.call_from)
                self.handle_missed_call(phone_call=phone_call, ctx={'user': user})
            except Exception as e:
                logger.error(e, exc_info=True)
                return HttpResponse('Failed to send missed call message.', status=500)

        return HttpResponse("Client leg status handled", status=200)
    
    def handle_missed_call(self, phone_call: PhoneCall, ctx: dict):
        lead_phone_number = phone_call.call_from if phone_call.is_inbound else phone_call.call_to
        user = ctx.get('user')
        lead = Lead.objects.filter(phone_number=lead_phone_number).first()
        outbound_calls = PhoneCall.objects.filter(call_to=lead_phone_number).count()
        inbound_calls = PhoneCall.objects.filter(call_from=lead_phone_number).count()
        is_first_call = inbound_calls + outbound_calls == 1

        scenarios = [
            {
                'name': 'first_inbound_call_missed',
                'text': lambda: "Hi! This is YD Cocktails, sorry we missed your call. We'll get back to you shortly.",
                'condition': is_first_call and phone_call.is_inbound,
                'text_from': phone_call.call_to,
                'text_to': phone_call.call_from,
            },
            {
                'name': 'first_outbound_call_missed',
                'text': lambda: "Hi! This is YD Cocktails, we just tried giving you a call about the bartending service but couldn't connect, please feel free to reach out whenever.",
                'condition': is_first_call and not phone_call.is_inbound,
                'text_from': phone_call.call_from,
                'text_to': phone_call.call_to,
            },
            {
                'name': 'inbound_call_missed',
                'text': lambda: f'Missed call from: {lead.full_name}',
                'condition': lead is not None and not is_first_call and phone_call.is_inbound,
                'text_from': settings.COMPANY_PHONE_NUMBER,
                'text_to': user.forward_phone_number,
            },
        ]

        for scenario in scenarios:
            if not scenario.get('condition'):
                continue

            try:
                message = Message(
                    text=scenario.get('text')(),
                    text_from=scenario.get('text_from'),
                    text_to=scenario.get('text_to'),
                    is_inbound=False,
                    status='pending',
                    is_read=True
                )

                resp = messaging_service.send_text_message(message=message)

                message.external_id = resp.sid
                message.status = resp.status
                message.save()
            except Exception as e:
                logger.error(e, exc_info=True)
                raise Exception('Error handling missed call.')