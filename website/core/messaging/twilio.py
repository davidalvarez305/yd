import mimetypes
import os
import uuid
import requests

from django.http import HttpRequest, HttpResponse
from django.core.files.base import ContentFile

from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.twiml.messaging_response import MessagingResponse

from core.utils import create_generic_file_name, download_file_from_twilio
from core.models import Message, MessageMedia

from communication.forms import MessageForm
from .base import MessagingServiceInterface
from .utils import strip_country_code

from website.settings import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, UPLOADS_URL

class TwilioMessagingService(MessagingServiceInterface):
    def __init__(self):
        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        self.validator = RequestValidator(TWILIO_AUTH_TOKEN)

    def handle_inbound_message(self, request: HttpRequest) -> HttpResponse:
        if request.method != "POST":
            response = MessagingResponse()
            response.message("Only POST allowed")
            return HttpResponse(str(response), content_type="application/xml", status=405)

        """ valid = self.validator.validate(
            request.build_absolute_uri(),
            request.POST,
            request.META.get("HTTP_X_TWILIO_SIGNATURE", "")
        )

        if not valid:
            response = MessagingResponse()
            response.message("Invalid Twilio signature.")
            return HttpResponse(str(response), content_type="application/xml", status=403) """

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

                ext = mimetypes.guess_extension(content_type)
                file_name = str(uuid.uuid4()) + ext

                local_file_path = os.path.join(UPLOADS_URL, file_name)

                if media_url:
                    download_file_from_twilio(twilio_resource=media_url, local_file_path=local_file_path)
                    with open(local_file_path, 'rb') as file:
                        content_file = ContentFile(file.read())

                        media = MessageMedia(message=message, content_type=content_type)
                        media.file.save(file_name, content_file)

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
            print("Message sent. Twilio response received.")

            if not response.sid:
                print("Error: Twilio response missing SID.")
                raise Exception("Twilio message SID not returned.")

            print(f"Twilio Message SID: {response.sid}")
            print(f"Twilio Message Status: {response.status}")
            return response

        except TwilioRestException as e:
            print("TwilioRestException caught!")
            print(f"Status: {e.status}")
            print(f"Code: {e.code}")
            print(f"Message: {e.msg}")
            raise Exception(f"TwilioRestException: {e.msg}") from e

        except Exception as e:
            print("General exception caught while sending text message.")
            print(f"Exception type: {type(e).__name__}")
            print(f"Exception details: {e}")
            raise