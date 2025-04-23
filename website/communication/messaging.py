from abc import ABC, abstractmethod
import requests

from django.http import HttpRequest
from django.core.files.base import ContentFile

from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from .forms import MessageForm
from .models import Message, MessageMedia
from .utils import strip_country_code, create_generic_file_name
from website.settings import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, DEBUG

class MessagingServiceInterface(ABC):
    @abstractmethod
    def handle_inbound_message(self, request: HttpRequest) -> None:
        pass

    @abstractmethod
    def handle_outbound_message(self, request: HttpRequest) -> None:
        pass

    @abstractmethod
    def _send_text_message(self, message: Message) -> None:
        pass

class TwilioMessagingService(MessagingServiceInterface):
    def __init__(self, client: Client, validator: RequestValidator):
        self.client = client
        self.validator = validator

    def handle_inbound_message(self, request) -> None:
        valid = self.validator.validate(
            request.build_absolute_uri(),
            request.POST,
            request.META.get("HTTP_X_TWILIO_SIGNATURE", "")
        )

        if not valid:
            raise ValueError("Invalid Twilio signature.")

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
                    raise RuntimeError(f"Failed to fetch media from URL: {media_url}")

        return message

    def handle_outbound_message(self, request: HttpRequest) -> None:
        form = MessageForm(request.POST, request.FILES)

        if not form.is_valid():
            raise Exception("Invalid form submitted.")
        
        message = form.save(commit=False)
        message.text_from = request.user.phone_number
        message.text_to = form.cleaned_data.get("text_to")
        message.is_inbound = False
        message.is_read = True

        media_files = form.cleaned_data.get('message_media', [])
        media_urls = []

        temp_media = []
        for file in media_files:
            file_name = create_generic_file_name(file.content_type)

            media = MessageMedia(
                message=None,
                content_type=file.content_type,
            )
            media.file.save(file_name, file, save=False)
            media_urls.append(media.file.url)
            temp_media.append(media)

        response = self._send_text_message(message, media_urls)

        message.external_id = response.sid
        message.save()

        for media in temp_media:
            media.message = message
            media.save()

    def _send_text_message(self, message: Message, media_urls: list[str] = None):
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
            raise Exception(f"Twilio error: {e.msg}") from e

class MessagingService:
    def __init__(self):
        self.service = MessagingServiceFactory.get_service()

    def handle_inbound_message(self, request: HttpRequest):
        return self.service.handle_inbound_message(request)

    def handle_outbound_message(self, request: HttpRequest):
        return self.service.handle_outbound_message(request)
    
class MessagingServiceFactory:
    @staticmethod
    def get_service() -> MessagingServiceInterface:
        """
        Returns the appropriate messaging service instance
        based on the current environment.
        """
        if DEBUG:
            return MessagingServiceFactory._create_twilio_service()
        return MessagingServiceFactory._create_twilio_service()

    @staticmethod
    def _create_twilio_service() -> TwilioMessagingService:
        client = Client(auth_token=TWILIO_AUTH_TOKEN, account_sid=TWILIO_ACCOUNT_SID)
        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        return TwilioMessagingService(client=client, validator=validator)