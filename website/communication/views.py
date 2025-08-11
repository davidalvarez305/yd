import json
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
import requests

from crm.views import CRMCreateView
from core.enums import AlertStatus
from core.mixins import AlertMixin
from core.models import Lead, Message, PhoneCallTranscription
from core.messaging import messaging_service
from core.calling import calling_service
from core.logger import logger
from core.transcription import transcription_service
from communication.forms import OutboundPhoneCallForm
from core.utils import get_transcription_external_id_from_object_key

from .forms import MessageForm

@csrf_exempt
def handle_inbound_message(request: HttpRequest):
    return messaging_service.handle_inbound_message(request)

@csrf_exempt
def handle_message_status_callback(request: HttpRequest):
    return messaging_service.handle_message_status_callback(request)

@csrf_exempt
def handle_transcription_subcription_callback(request: HttpRequest):
    message_type = request.headers.get("x-amz-sns-message-type")
    payload = json.loads(request.body)

    # Step 1: Confirm subscription if needed
    if message_type == "SubscriptionConfirmation":
        subscribe_url = payload.get('SubscribeURL')
        requests.get(subscribe_url)
        return HttpResponse("Subscription confirmed", status=200)

    # Step 2: Handle notification
    if message_type == "Notification":
        message = json.loads(payload.get('Message'))
        records = message.get("Records", [])
        if not records:
            return HttpResponse(status=400)
        
        s3_object_key = records[0].get("s3", {}).get("object", {}).get("key")
        if not s3_object_key:
            return HttpResponse(status=400)

        external_id = get_transcription_external_id_from_object_key(s3_object_key)
        transcription = PhoneCallTranscription.objects.filter(external_id=external_id).first()
        
        if not transcription:
            return HttpResponse(status=400)
        
        transcription_service.process_transcription(transcription=transcription)

    return HttpResponse(status=200)

class MessageCreateView(CRMCreateView):
    model = Message
    form_class = MessageForm

    def form_valid(self, form):
        try:
            messaging_service.handle_outbound_message(form)

            lead = Lead.objects.filter(phone_number=form.cleaned_data.get('text_to')).first()

            return render(self.request, 'crm/lead_chat_messages.html', { 'lead': lead })

        except Exception as e:
            logger.error("Failed to handle outbound message", exc_info=True)
            return self.alert(self.request, str(e), AlertStatus.INTERNAL_ERROR)

    def form_invalid(self, form):
        return self.alert(self.request, form.errors.as_text(), AlertStatus.BAD_REQUEST)

@csrf_exempt
def handle_inbound_call(request: HttpRequest):
    return calling_service.handle_inbound_call(request)

@csrf_exempt
def handle_call_status_callback(request: HttpRequest):
    return calling_service.handle_call_status_callback(request)

@csrf_exempt
def handle_outbound_call_status_callback(request: HttpRequest):
    return calling_service.handle_outbound_call_status_callback(request)

@csrf_exempt
def handle_call_recording_callback(request: HttpRequest):
    return calling_service.handle_call_recording_callback(request)

class OutboundCallView(LoginRequiredMixin, AlertMixin, CreateView):
    def post(self, request):
        form = OutboundPhoneCallForm(request.POST)

        if not form.is_valid():
            return self.alert(request, "Invalid form data", AlertStatus.BAD_REQUEST)

        try:
            calling_service.handle_outbound_call(ctx=form.cleaned_data)
            return HttpResponse("Success!", status=200)
        except Exception as e:
            logger.error(e, exc_info=True)
            return self.alert(request, "Failed to initiate outbound call", AlertStatus.INTERNAL_ERROR)