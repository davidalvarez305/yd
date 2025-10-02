import json
import mimetypes
import os
import uuid

from django.http import HttpResponse
from django.core.files.base import ContentFile
from django.core.files import File
import requests

from core.logger import logger
from core.call_tracking.base import CallingTrackingServiceInterface
from website import settings

from core.models import (
    Message,
    MessageMedia,
    PhoneCall,
    PhoneCallTranscription,
    TrackingPhoneCall,
    TrackingPhoneCallMetadata,
    TrackingTextMessage,
    TrackingTextMessageMetadata,
    User,
)
from core.utils import cleanup_dir_files, convert_audio_format, convert_video_to_mp4, create_generic_file_name, download_file_from_url, get_content_type_from_url
from core.messaging.utils import MIME_EXTENSION_MAP
from core.transcription import transcription_service
from core.calling import calling_service

CALLRAIL_FIELDS = [
    "agent_email",
    "call_highlights",
    "call_summary",
    "call_type",
    "campaign",
    "company_id",
    "company_name",
    "company_time_zone",
    "conversational_transcript",
    "created_at",
    "custom",
    "device_type",
    "fbclid",
    "first_call",
    "formatted_call_type",
    "formatted_customer_location",
    "formatted_business_phone_number",
    "formatted_customer_name",
    "formatted_customer_name_or_phone_number",
    "formatted_customer_phone_number",
    "formatted_duration",
    "formatted_tracking_phone_number",
    "formatted_tracking_source",
    "formatted_value",
    "ga",
    "gclid",
    "good_lead_call_id",
    "good_lead_call_time",
    "integration_data",
    "keypad_entries",
    "keywords",
    "keywords_spotted",
    "landing_page_url",
    "last_requested_url",
    "lead_status",
    "medium",
    "milestones",
    "msclkid",
    "note",
    "person_id",
    "prior_calls",
    "referrer_domain",
    "referring_url",
    "sentiment",
    "session_uuid",
    "source",
    "source_name",
    "speaker_percent",
    "tags",
    "timeline_url",
    "total_calls",
    "tracker_id",
    "transcription",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
    "value",
    "voice_assist_message",
    "waveforms",
    "zip_code",
]

class CallRailTrackingService(CallingTrackingServiceInterface):
    def __init__(self):
        self.account_id = settings.CALL_RAIL_ACCOUNT_ID
        self.api_key = settings.CALL_RAIL_API_KEY

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
    
    def handle_inbound_tracking_call_end(self, request) -> HttpResponse:
        try:
            data = json.loads(request.body.decode("utf-8"))

            resource_id = data.get('resource_id')
            tracking_phone_call = TrackingPhoneCall.objects.get(external_id=resource_id)
            tracking_phone_call.status = data.get('call_type')
            tracking_phone_call.call_duration = int(data.get("duration", 0))
            tracking_phone_call.save()

            recording_url = self.get_public_recording_url(call_id=resource_id)

            phone_call = PhoneCall(
                external_id=resource_id,
                call_duration=tracking_phone_call.call_duration,
                date_created=tracking_phone_call.date_created,
                call_from=tracking_phone_call.call_from,
                call_to=tracking_phone_call.call_to,
                is_inbound=True,
                recording_url=recording_url,
                status=tracking_phone_call.status,
            )

            phone_call.save()

            if not data.get('answered'):
                ctx = {
                    'user': User.objects.get(phone_number="+1" + settings.COMPANY_PHONE_NUMBER)
                }
                calling_service.handle_missed_call(phone_call=phone_call, ctx=ctx)
                return HttpResponse(status=200)
            
            if not recording_url:
                return HttpResponse(status=200)

            job_name = str(uuid.uuid4())
            audio_filename = job_name + ".mp3"
            local_audio_path = os.path.join(settings.UPLOADS_URL, audio_filename)

            download_file_from_url(recording_url, local_audio_path)

            try:
                with open(local_audio_path, 'rb') as audio_file:
                    transcription = PhoneCallTranscription(
                        phone_call=phone_call,
                        external_id=job_name,
                        audio=File(audio_file, name=audio_filename)
                    )
                    transcription.save()

                transcription_service.transcribe_audio(transcription=transcription)

            finally:
                cleanup_dir_files(settings.UPLOADS_URL)

            return HttpResponse(status=200)

        except Exception as e:
            logger.error("Error handling CallRail webhook (call)", exc_info=True)
            return HttpResponse("An unexpected error occurred.", status=500)

    def handle_inbound_tracking_message(self, request) -> HttpResponse:
        try:
            data = json.loads(request.body.decode("utf-8"))

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
                headers = {
                    "Authorization": f"Token token={self.api_key}"
                }
                download_file_from_url(url=media_url, local_file_path=source_file_path, headers=headers)

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
    
    def get_call_by_id(self, call_id: str):
        url = f"https://api.callrail.com/v3/a/{self.account_id}/calls/{call_id}.json"
        headers = {
            "Authorization": f"Token token={self.api_key}"
        }
        params = {
            "fields": ",".join(CALLRAIL_FIELDS)
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_public_recording_url(self, call_id: str):
        url = f"https://api.callrail.com/v3/a/{self.account_id}/calls/{call_id}/recording.json"
        headers = {
            "Authorization": f"Token token={self.api_key}"
        }

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 404:
                logger.warning(f"Recording not found for call_id={call_id}")
                return None

            response.raise_for_status()

            try:
                data = response.json()
            except ValueError:
                logger.error(f"Invalid JSON response for call_id={call_id}")
                return None

            return data.get("url")

        except requests.RequestException as e:
            logger.error(f"Failed to fetch recording for call_id={call_id}: {e}")
            return None