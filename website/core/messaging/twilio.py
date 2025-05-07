import requests

from django.http import HttpRequest, HttpResponse
from django.core.files.base import ContentFile

from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.twiml.messaging_response import MessagingResponse

from core.utils import create_generic_file_name
from core.models import Message, MessageMedia

from communication.forms import MessageForm

from .base import MessagingServiceInterface
from .utils import strip_country_code
from website.settings import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN

class TwilioMessagingService(MessagingServiceInterface):
    def __init__(self):
        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        self.validator = RequestValidator(TWILIO_AUTH_TOKEN)

    def handle_inbound_message(self, request: HttpRequest) -> HttpResponse:
        if request.method != "POST":
            response = MessagingResponse()
            response.message("Only POST allowed")
            return HttpResponse(str(response), content_type="application/xml", status=405)

        valid = self.validator.validate(
            request.build_absolute_uri(),
            request.POST,
            request.META.get("HTTP_X_TWILIO_SIGNATURE", "")
        )

        if not valid:
            response = MessagingResponse()
            response.message("Invalid Twilio signature.")
            return HttpResponse(str(response), content_type="application/xml", status=403)

        try:
            message_sid = request.POST.get("MessageSid")
            text_from = strip_country_code(request.POST.get("From"))
            text_to = strip_country_code(request.POST.get("To"))
            body = request.POST.get("Body", "")
            num_media = int(request.POST.get("NumMedia", 0))
            sms_status = request.POST.get("SmsStatus")

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
                        file_name = create_generic_file_name(content_type)
                        content_file = ContentFile(response.content)
                        media = MessageMedia(message=message, content_type=content_type)
                        media.file.save(file_name, content_file)
                    else:
                        response = MessagingResponse()
                        response.message(f"Failed to download media: {media_url}")
                        return HttpResponse(str(response), content_type="application/xml", status=502)

            response = MessagingResponse()
            response.message("Message received successfully.")
            return HttpResponse(str(response), content_type="application/xml", status=200)

        except Exception as e:
            print(f"Unexpected error in handle_inbound_message: {e}")
            response = MessagingResponse()
            response.message("Unexpected error occurred.")
            return HttpResponse(str(response), content_type="application/xml", status=500)

    def handle_outbound_message(self, form: MessageForm) -> None:
        message = form.save(commit=False)
        message.text_from = form.cleaned_data.get("text_from")
        message.text_to = form.cleaned_data.get("text_to")
        message.is_inbound = False
        message.is_read = True

        media_urls = []
        temp_media = []

        media_files = form.cleaned_data.get('message_media') or []
        if media_files:
            for file in media_files:
                content_type = file.content_type

                media = MessageMedia(
                    message=None,
                    content_type=content_type,
                )
                media.file.save(file.name, file, save=False)
                media_urls.append(media.file.url)
                temp_media.append(media)

        response = self.send_text_message(message, media_urls)

        message.external_id = response.sid
        message.save()

        for media in temp_media:
            media.message = message
            media.save()

    def send_text_message(self, message: Message, media_urls: list[str] = None):
        try:
            response = self.client.messages.create(
                to=message.text_to,
                from_=message.text_from,
                body=message.text,
                media_url=media_urls if media_urls else None
            )

            if not response.sid:
                raise Exception("Twilio message SID not returned.")

            return response

        except TwilioRestException as e:
            raise Exception(e.msg) from e