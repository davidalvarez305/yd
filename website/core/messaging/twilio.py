import mimetypes
import os
import uuid

from django.http import HttpRequest, HttpResponse
from django.core.files.base import ContentFile

from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.twiml.messaging_response import MessagingResponse

from core.utils import cleanup_dir_files, convert_audio_format, convert_video_to_mp4, download_file_from_twilio
from core.models import Message, MessageMedia

from communication.forms import MessageForm
from communication.enums import TwilioWebhookCallbacks
from .base import MessagingServiceInterface
from .utils import MIME_EXTENSION_MAP, strip_country_code
from core.logger import logger

from website.settings import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, UPLOADS_URL, DEBUG

class TwilioMessagingService(MessagingServiceInterface):
    def __init__(self):
        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        self.validator = RequestValidator(TWILIO_AUTH_TOKEN)

    def handle_inbound_message(self, request: HttpRequest) -> HttpResponse:
        if request.method != "POST":
            return HttpResponse("Only POST allowed", status=405)

        if not DEBUG:
            valid = self.validator.validate(
                request.build_absolute_uri(),
                request.POST,
                request.META.get("HTTP_X_TWILIO_SIGNATURE")
            )

            if not valid:
                return HttpResponse("Invalid Twilio signature.", status=403)

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

                ext = mimetypes.guess_extension(content_type) or MIME_EXTENSION_MAP.get(content_type, '.bin')
                original_file_name = str(uuid.uuid4()) + ext
                original_file_path = os.path.join(UPLOADS_URL, original_file_name)

                if not (media_url and content_type):
                    continue

                # Download the media file
                download_file_from_twilio(twilio_resource=media_url, local_file_path=original_file_path)

                # Handle audio conversion to mp3
                if content_type.startswith("audio/") and 'mp3' not in ext:
                    converted_filename = str(uuid.uuid4()) + '.mp3'
                    converted_content_type = "audio/mpeg"

                    with open(original_file_path, 'rb') as original_file:
                        converted_buffer = convert_audio_format(file=original_file, file_path=original_file_path, to_format=".mp3")

                    media = MessageMedia(message=message, content_type=converted_content_type)
                    media.file.save(converted_filename, ContentFile(converted_buffer.read()))

                # Handle video conversion to mp4
                elif content_type.startswith("video/"):
                    converted_filename = str(uuid.uuid4()) + '.mp4'
                    converted_path = os.path.join(UPLOADS_URL, converted_filename)

                    convert_video_to_mp4(original_file_path, converted_path)

                    with open(converted_path, 'rb') as video_file:
                        media = MessageMedia(message=message, content_type='video/mp4')
                        media.file.save(converted_filename, ContentFile(video_file.read()))
                else:
                    # Handle image files
                    with open(original_file_path, 'rb') as f:
                        media = MessageMedia(message=message, content_type=content_type)
                        media.file.save(original_file_name, ContentFile(f.read()))

        except Exception as e:
            logger.error(e, exc_info=True)
            return HttpResponse("Unexpected error occurred.", status=500)

        finally:
            cleanup_dir_files(UPLOADS_URL)

        return HttpResponse("Message received successfully.", status=200)

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
            status_callback = TwilioWebhookCallbacks.get_full_url(TwilioWebhookCallbacks.MESSAGE_STATUS_CALLBACK.value)
            
            response = self.client.messages.create(
                to=message.text_to,
                from_=message.text_from,
                body=message.text,
                status_callback=status_callback,
                media_url=media_urls if media_urls else None
            )

            if not response.sid:
                raise Exception("Twilio message SID not returned.")

            return response

        except TwilioRestException as e:
            raise Exception(f"TwilioRestException: {e.msg}") from e

        except Exception as e:
            raise
    
    def handle_message_status_callback(self, request) -> HttpResponse:
        if request.method != "POST":
            return HttpResponse("Only POST allowed", status=405)

        if not DEBUG:
            valid = self.validator.validate(
                request.build_absolute_uri(),
                request.POST,
                request.META.get("HTTP_X_TWILIO_SIGNATURE", "")
            )

            if not valid:
                return HttpResponse("Invalid Twilio signature", status=403)

        message_sid = request.POST.get("MessageSid")
        message_status = request.POST.get("MessageStatus")

        if not message_sid:
            return HttpResponse("Missing MessageSid", status=400)

        try:
            message = Message.objects.get(external_id=message_sid)
            message.status = message_status
            message.save()
            return HttpResponse(status=204)
        except Message.DoesNotExist:
            return HttpResponse("Message not found", status=404)