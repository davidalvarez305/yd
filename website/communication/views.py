from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest
from django.shortcuts import render

from crm.views import CRMBaseCreateView
from core.enums import AlertStatus
from core.mixins import AlertMixin
from core.attachments import AttachmentServiceMixin
from core.models import Lead, Message
from core.messaging import messaging_service
from core.calling import calling_service
from .forms import MessageForm

@csrf_exempt
def handle_inbound_message(request: HttpRequest):
    return messaging_service.handle_inbound_message(request)

@csrf_exempt
def handle_message_status_callback(request: HttpRequest):
    return messaging_service.handle_message_status_callback(request)

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
            messaging_service.handle_outbound_message(form)

            lead = Lead.objects.filter(phone_number=form.cleaned_data.get('text_to')).first()

            return render(request, 'crm/lead_chat_messages.html', { 'lead': lead })
        except Exception as e:
            return self.alert(request, f'{str(e)}', AlertStatus.INTERNAL_ERROR)

@csrf_exempt
def handle_inbound_call(request: HttpRequest):
    return calling_service.handle_inbound_call(request)

@csrf_exempt
def handle_outbound_call(request: HttpRequest):
    return calling_service.handle_outbound_call(request)

@csrf_exempt
def handle_call_status_callback(request: HttpRequest):
    return calling_service.handle_call_status_callback(request)

@csrf_exempt
def handle_call_recording_callback(request: HttpRequest):
    return calling_service.handle_call_recording_callback(request)