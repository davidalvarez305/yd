import uuid
import requests

from twilio.request_validator import RequestValidator

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.core.files.base import ContentFile

from .models import Message, MessageMedia
from crm.models import Message
from website.settings import TWILIO_AUTH_TOKEN

def strip_country_code(phone_number):
    return phone_number[-10:] if phone_number else ''

@csrf_exempt
def handle_inbound_message(request):
    if request.method != "POST":
        return JsonResponse({'data': 'Only POST allowed'}, status=405)

    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    valid = validator.validate(
        request.build_absolute_uri(),
        request.POST,
        request.META.get("HTTP_X_TWILIO_SIGNATURE", "")
    )

    if not valid:
        return HttpResponse("Invalid Twilio signature", status=403)

    try:
        message_sid = request.POST.get("MessageSid")
        text_from = strip_country_code(request.POST.get("From"))
        text_to = strip_country_code(request.POST.get("To"))
        body = request.POST.get("Body", "")
        num_media = int(request.POST.get("NumMedia", 0))
        sms_status = request.POST.get("SmsStatus", "received")

        if not message_sid:
            return JsonResponse({'data': 'Missing MessageSid'}, status=400)

        message = Message.objects.create(
            external_id=message_sid,
            text=body,
            text_from=text_from,
            text_to=text_to,
            is_inbound=True,
            status=sms_status,
            is_read=False,
        )

        for i in range(num_media):
            media_url = request.POST.get(f"MediaUrl{i}")
            content_type = request.POST.get(f"MediaContentType{i}")

            if media_url:
                response = requests.get(media_url)
                if response.status_code == 200:
                    extension = content_type.split("/")[-1]
                    file_name = f"{uuid.uuid4()}.{extension}"

                    content_file = ContentFile(response.content)
                    media = MessageMedia(
                        message=message,
                        content_type=content_type,
                    )
                    media.file.save(file_name, content_file)

        return JsonResponse({'status': 'ok'}, status=201)

    except Exception as e:
        return JsonResponse({'data': f"Internal Server Error: {str(e)}"}, status=500)