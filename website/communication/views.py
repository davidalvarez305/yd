from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError, JsonResponse, HttpRequest
from django.shortcuts import render
from django.utils.timezone import now

from twilio.twiml.voice_response import VoiceResponse, Dial
from twilio.twiml.messaging_response import MessagingResponse

from crm.views import CRMBaseCreateView
from core.enums import AlertStatus
from core.mixins import AlertMixin
from core.attachments import AttachmentServiceMixin
from core.models import Lead, User
from website import settings

from .enums import TwilioWebhookCallbacks, TwilioWebhookEvents
from .utils import strip_country_code
from .messaging import MessagingService
from .models import Message, PhoneCall
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
    if request.method != "POST":
        response = VoiceResponse()
        response.say("Only POST allowed")
        return HttpResponse(str(response), content_type="application/xml", status=405)

    try:
        form = request.POST
        call_sid = form.get("CallSid")
        call_from = form.get("From")
        call_to = form.get("To")
        call_status = form.get("CallStatus")

        if not all([call_sid, call_from, call_to, call_status]):
            response = VoiceResponse()
            response.say("Missing required fields")
            return HttpResponseBadRequest(str(response))

        from_number = strip_country_code(call_from)
        to_number = strip_country_code(call_to)

        forward = User.objects.filter(phone_number=to_number).first()
        if not forward:
            raise ValueError("No matching phone number")
        forward_number = forward.phone_number

        recording_callback_url = TwilioWebhookCallbacks.get_full_url(TwilioWebhookCallbacks.INBOUND.value)
        action_url = TwilioWebhookCallbacks.get_full_url(TwilioWebhookCallbacks.STATUS.value)

        response = VoiceResponse()
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
        response = VoiceResponse()
        response.say(f"Server error: {e}")
        print(f"Server error: {e}")
        return HttpResponse(str(response), content_type="application/xml", status=500)

@csrf_exempt
def handle_call_status_callback(request):
    if request.method == 'POST':
        dial_call_status = request.POST.get("DialCallStatus")
        call_sid = request.POST.get("CallSid")
        dial_call_duration = request.POST.get("DialCallDuration", "0")

        try:
            phone_call = PhoneCall.objects.get(call_sid=call_sid)

            phone_call.call_duration = int(dial_call_duration)
            phone_call.status = dial_call_status

            phone_call.save()

            return HttpResponse("<Response></Response>", content_type="application/xml", status=200)

        except PhoneCall.DoesNotExist:
            return HttpResponse("<Response><Error>Phone call not found</Error></Response>", content_type="application/xml", status=404)

        except Exception as e:
            return HttpResponse(f"<Response><Error>{str(e)}</Error></Response>", content_type="application/xml", status=500)

    return HttpResponse("<Response><Error>Invalid request method</Error></Response>", content_type="application/xml", status=405)