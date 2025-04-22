from abc import ABC, abstractmethod
import requests
import uuid

from django.shortcuts import get_object_or_404
from django.http import HttpRequest
from django.core.files.base import ContentFile

from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from communication.forms import MessageForm
from core.models import Lead
from website.settings import TWILIO_AUTH_TOKEN, TWILIO_ACCOUNT_SID

from .enums import MessagingProvider
from .models import Message, MessageMedia
from .utils import strip_country_code

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
    def __init__(self, auth_token: str, account_sid: str):
        self.auth_token = auth_token
        self.validator = RequestValidator(self.auth_token)
        self.account_sid = account_sid

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
                    extension = content_type.split("/")[-1]
                    file_name = f"{uuid.uuid4()}.{extension}"

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
        message.text_from = "7869987121"
        message.text_to = form.cleaned_data.get("text_to")
        message.is_inbound = False
        message.is_read = True

        media_files = form.cleaned_data.get('message_media', [])
        media_urls = []

        temp_media = []
        for file in media_files:
            media = MessageMedia(
                message=None,
                content_type=file.content_type,
            )
            media.file.save(file.name, file, save=False)
            media_urls.append(media.file.url)
            temp_media.append(media)

        response = self._send_text_message(message, media_urls)

        message.external_id = response.sid
        message.save()

        for media in temp_media:
            media.message = message
            media.save()

    def _send_text_message(self, message: Message, media_urls: list[str] = None):
        client = Client(self.account_sid, self.auth_token)

        try:
            response = client.messages.create(
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
    def __init__(self, provider: MessagingProvider):
        self.provider = provider
        self.service = self._get_service()

    def _get_service(self) -> MessagingServiceInterface:
        if self.provider == MessagingProvider.TWILIO:
            return TwilioMessagingService(auth_token=TWILIO_AUTH_TOKEN, account_sid=TWILIO_ACCOUNT_SID)
        raise ValueError(f"Unknown provider: {self.provider}")

    def handle_inbound_message(self, request: HttpRequest):
        return self.service.handle_inbound_message(request)

    def handle_outbound_message(self, request: HttpRequest):
        return self.service.handle_outbound_message(request)