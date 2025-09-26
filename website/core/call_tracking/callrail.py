import json
import mimetypes
import os

from django.http import HttpResponse
from django.core.files.base import ContentFile

from core.logger import logger
from core.call_tracking.base import CallingTrackingServiceInterface
from website import settings

from core.models import (
    Message,
    MessageMedia,
    TrackingPhoneCall,
    TrackingPhoneCallMetadata,
    TrackingTextMessage,
    TrackingTextMessageMetadata,
)
from core.utils import convert_audio_format, convert_video_to_mp4, create_generic_file_name, download_file_from_url, get_content_type_from_url
from core.messaging.utils import MIME_EXTENSION_MAP


class CallRailTrackingService(CallingTrackingServiceInterface):
    def handle_inbound_tracking_call(self, request) -> HttpResponse:
        try:
            data = json.loads(request.body.decode("utf-8"))

            tracking_phone_call = TrackingPhoneCall.objects.create(
                external_id=data.get("resource_id"),
                call_duration=int(data.get("duration", 0)),
                call_from=data.get("customer_phone_number"),
                call_to=data.get("tracking_phone_number"),
                status=data.get("call_type"),
            )

            model_fields = {
                "resource_id",
                "duration",
                "customer_phone_number",
                "tracking_phone_number",
                "call_type",
            }

            for key, value in data.items():
                if key in model_fields:
                    continue

                if isinstance(value, (dict, list)):
                    value = json.dumps(value)

                TrackingPhoneCallMetadata.objects.create(
                    tracking_phone_call=tracking_phone_call,
                    key=key,
                    value=value,
                )

            return HttpResponse(status=200)

        except Exception as e:
            logger.error("Error handling CallRail webhook (call)", exc_info=True)
            return HttpResponse("An unexpected error occurred.", status=500)

    def handle_inbound_tracking_message(self, request) -> HttpResponse:
        try:
            data = json.loads(request.body.decode("utf-8"))

            print(data)
            for media in data.get('media_urls'):
                print(media)

            tracking_text = TrackingTextMessage.objects.create(
                external_id=data.get("resource_id"),
                message=data.get("content"),
                text_from=data.get("source_number"),
                text_to=data.get("destination_number"),
            )

            model_fields = {
                "resource_id",
                "content",
                "source_number",
                "destination_number",
            }

            for key, value in data.items():
                if key in model_fields:
                    continue

                if isinstance(value, (dict, list)):
                    value = json.dumps(value)

                TrackingTextMessageMetadata.objects.create(
                    tracking_text_message=tracking_text,
                    key=key,
                    value=value,
                )

            message = Message()
            message.external_id = tracking_text.external_id
            message.text = tracking_text.message
            message.text_from = tracking_text.text_from
            message.text_to = tracking_text.text_to
            message.is_inbound = True
            message.status = 'received'
            message.is_read = False
            message.is_notified = False
            message.save()

            for media_url in data.get('media_urls'):
                content_type = get_content_type_from_url(media_url)

                source_ext = mimetypes.guess_extension(content_type) or MIME_EXTENSION_MAP.get(content_type, '.bin')
                source_file_name = create_generic_file_name(content_type, source_ext)
                source_file_path = os.path.join(settings.UPLOADS_URL, source_file_name)

                # Download the media file
                download_file_from_url(twilio_resource=media_url, local_file_path=source_file_path)

                # Handle audio conversion to mp3
                if content_type.startswith("audio/"):
                    target_file_name = create_generic_file_name(content_type, '.mp3')
                    target_file_path = os.path.join(settings.UPLOADS_URL, target_file_name)
                    target_content_type = "audio/mpeg"

                    with open(source_file_path, 'rb') as source_file:
                        buffer = convert_audio_format(file=source_file, target_file_path=target_file_path, to_format="mp3")

                    media = MessageMedia(message=message, content_type=target_content_type)
                    media.file.save(target_file_name, ContentFile(buffer.read()))

                # Handle video conversion to mp4
                elif content_type.startswith("video/"):
                    target_file_name = create_generic_file_name(content_type, '.mp4')
                    target_file_path = os.path.join(settings.UPLOADS_URL, target_file_name)

                    convert_video_to_mp4(source_file_path, target_file_path)

                    with open(target_file_path, 'rb') as target_video_file:
                        media = MessageMedia(message=message, content_type='video/mp4')
                        media.file.save(target_file_name, ContentFile(target_video_file.read()))
                else:
                    # Handle image files
                    with open(source_file_path, 'rb') as f:
                        media = MessageMedia(message=message, content_type=content_type)
                        media.file.save(source_file_name, ContentFile(f.read()))

            return HttpResponse(status=200)

        except Exception as e:
            logger.error("Error handling CallRail webhook (text)", exc_info=True)
            return HttpResponse("An unexpected error occurred.", status=500)