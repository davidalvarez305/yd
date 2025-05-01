import os
import uuid
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from django.core.files import File

from twilio.twiml.messaging_response import MessagingResponse

from crm.views import CRMBaseCreateView
from core.enums import AlertStatus
from core.mixins import AlertMixin
from core.attachments import AttachmentServiceMixin
from core.models import Lead
from core.utils import download_file_from_url
from website import settings
from website.communication.calling import CallingService

from .transcription import TranscriptionService
from .messaging import MessagingService
from .models import Message, PhoneCallTranscription
from .forms import MessageForm

@csrf_exempt
def handle_inbound_message(request):
    if request.method != "POST":
        response = MessagingResponse()
        response.message('Only POST allowed')
        return HttpResponse(str(response), content_type="application/xml", status=405)

    try:
        service = MessagingService()
        service.handle_inbound_message(request)
        
        response = MessagingResponse()
        response.message('Message received successfully!')
        return HttpResponse(str(response), content_type="application/xml", status=200)

    except Exception as e:
        response = MessagingResponse()
        response.message(f"Unexpected error: {str(e)}")
        return HttpResponse(str(response), content_type="application/xml", status=500)

class MessageCreateView(AttachmentServiceMixin, CRMBaseCreateView, AlertMixin):
    model = Message
    form_class = MessageForm

    def post(self, request, *args, **kwargs):
        if request.method != "POST":
            return self.alert(request, "Only POST headers allowed.", AlertStatus.BAD_REQUEST)
            
        form = MessageForm(request.POST, request.FILES)

        if not form.is_valid():
            return self.alert(request, form.errors.as_text(), AlertStatus.BAD_REQUEST)

        try:
            service = MessagingService()
            service.handle_outbound_message(form)

            lead = Lead.objects.filter(phone_number=form.cleaned_data.get('text_to')).first()

            return render(request, 'crm/lead_chat_messages.html', { 'lead': lead })
        except Exception as e:
            return self.alert(request, f'{str(e)}', AlertStatus.INTERNAL_ERROR)

@csrf_exempt
def handle_inbound_call(request: HttpRequest):
    return CallingService().handle_inbound_call(request)

@csrf_exempt
def handle_call_status_callback(request: HttpRequest):
    return CallingService().handle_call_status(request)

@csrf_exempt
def handle_call_recording_callback(request: HttpRequest):
    return CallingService().handle_call_recording_callback(request)