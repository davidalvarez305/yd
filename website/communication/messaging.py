from abc import ABC, abstractmethod
import requests
import os
import subprocess
import tempfile

from django.core.files import File
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
        message.text_from = "7869987121"
        message.text_to = form.cleaned_data.get("text_to")
        message.is_inbound = False
        message.is_read = True

        media_files = form.cleaned_data.get('message_media', [])
        media_urls = []
        temp_media = []

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        for file in media_files:
            file_name = create_generic_file_name(file.content_type)
            content_type = file.content_type

            if content_type == "audio/webm":
                try:
                    webm_path = os.path.join(base_dir, f"audio_files/{file_name}").replace("\\", "/")
                    os.makedirs(os.path.dirname(webm_path), exist_ok=True)

                    with open(webm_path, "wb") as tmp_webm:
                        for chunk in file.chunks():
                            tmp_webm.write(chunk)

                    mp3_path = webm_path.replace(".webm", ".mp3")
                    print(webm_path)
                    print(mp3_path)

                    try:
                        command = f'ffmpeg -y -i "{webm_path}" -codec:a libmp3lame -qscale:a 2 "{mp3_path}"'
                        process = subprocess.run(
                            command,
                            shell=True,
                            check=True,
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE
                        )
                    except subprocess.CalledProcessError as e:
                        print("FFmpeg failed with error:")
                        print(e.stderr.decode())
                        raise

                    with open(mp3_path, "rb") as mp3_file:
                        django_file = File(mp3_file)
                        mp3_file_name = os.path.basename(mp3_path)

                        media = MessageMedia(
                            message=None,
                            content_type="audio/mpeg",
                        )
                        media.file.save(mp3_file_name, django_file, save=False)
                        media_urls.append(media.file.url)
                        temp_media.append(media)

                finally:
                    pass
                    """ # Clean up the webm and mp3 files
                    if os.path.exists(webm_path):
                        os.remove(webm_path)
                    if os.path.exists(mp3_path):
                        os.remove(mp3_path) """

            else:
                media = MessageMedia(
                    message=None,
                    content_type=content_type,
                )
                media.file.save(file_name, file, save=False)
                media_urls.append(media.file.url)
                temp_media.append(media)

        # Send the message with the media
        response = self._send_text_message(message, media_urls)

        # Save the message with external ID
        message.external_id = response.sid
        message.save()

        # Save media associations
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
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        return TwilioMessagingService(client=client, validator=validator)