from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpRequest
from django.shortcuts import render

from crm.views import CRMBaseCreateView
from core.enums import AlertStatus
from core.mixins import AlertMixin
from core.attachments import AttachmentServiceMixin
from core.models import Lead

from .messaging import MessagingService
from .models import Message
from .forms import MessageForm

@csrf_exempt
def handle_inbound_message(request: HttpRequest):
    if request.method != "POST":
        return JsonResponse({'data': 'Only POST allowed'}, status=405)

    try:
        service = MessagingService()
        service.handle_inbound_message(request)
        return JsonResponse({'data': 'ok'}, status=200)
    except Exception as e:
        return JsonResponse({'data': f'Unexpected error: {str(e)}'}, status=500)

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