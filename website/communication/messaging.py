from abc import ABC, abstractmethod
from django.shortcuts import get_object_or_404
import requests
import uuid

from django.core.files.base import ContentFile

from twilio.request_validator import RequestValidator
from twilio.rest import Client

from communication.forms import MessageForm
from core.models import Lead
from website.settings import TWILIO_AUTH_TOKEN

from .enums import MessagingProvider
from .models import Message, MessageMedia
from .utils import strip_country_code

class MessagingServiceInterface(ABC):
    @abstractmethod
    def handle_inbound_message(self, request):
        pass

    @abstractmethod
    def handle_outbound_message(self, request):
        pass

class TwilioMessagingService(MessagingServiceInterface):
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.validator = RequestValidator(self.auth_token)

    def handle_inbound_message(self, request):
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
                    media = MessageMedia(
                        message=message,
                        content_type=content_type,
                    )
                    media.file.save(file_name, content_file)
                else:
                    raise RuntimeError(f"Failed to fetch media from URL: {media_url}")

        return message

    def handle_outbound_message(self, to: str, body: str):
        return f"Twilio: Sent to {to}"
    
    def _send_text_message(self, request, lead_id) -> dict:
        """
        Sends a text message via Twilio and returns the message object as a dict.
        """
        client = Client(self.account_sid, self.auth_token)

        form = MessageForm(request.POST)
        if form.valid:
            lead = get_object_or_404(Lead, pk=lead_id)

            message = form.save(commit=False)
            message.text_from = request.user.phone_number
            message.text_to = lead.phone_number
            message.is_inbound = False
            message.is_read = True
            message.save()

            for file in form.cleaned_data.get('message_media', []):
                media = MessageMedia(
                    message=message,
                    content_type=file.content_type,
                )
                media.file.save(file.name, file)

            response = client.messages.create(
                to=message.text_to,
                from_=message.text_from,
                body=message.message,
            )

            if not response.status.code == 200:
                raise Exception("Error sending outbound message.")

            return message
        else:
            raise Exception("Invalid form submitted.")

class MessagingService:
    def __init__(self, provider: MessagingProvider):
        self.provider = provider
        self.service = self._get_service()

    def _get_service(self) -> MessagingServiceInterface:
        if self.provider == MessagingProvider.TWILIO:
            return TwilioMessagingService(auth_token=TWILIO_AUTH_TOKEN)
        raise ValueError(f"Unknown provider: {self.provider}")

    def handle_inbound_message(self, request):
        return self.service.handle_inbound_message(request)

    def handle_outbound_message(self, to: str, body: str):
        return self.service.handle_outbound_message(to, body)