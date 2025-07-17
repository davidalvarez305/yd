import os
import json
import mimetypes

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from core.messaging import messaging_service
from core.messaging.utils import MIME_EXTENSION_MAP
from core.models import Message, MessageMedia
from core.utils import convert_audio_format, convert_video_to_mp4, create_generic_file_name, download_file_from_twilio

from website.settings import UPLOADS_URL

class Command(BaseCommand):
    help = 'Fetch Twilio messages and either save to DB or export to JSON.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--save',
            action='store_true',
            help='Save messages to the database'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Export messages to data.json'
        )

    def handle(self, *args, **options):
        messages = messaging_service.get_all_messages()

        if options['json']:
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            self.stdout.write(self.style.SUCCESS(f"✅ Exported {len(messages)} messages to data.json"))

        if options['save']:
            count = 0
            for msg in messages:
                try:
                    message = Message(
                        external_id=msg.get('sid'),
                        text=msg.get('body'),
                        text_from=msg.get('from'),
                        text_to=msg.get('to'),
                        is_inbound=(msg.get('direction') == 'inbound'),
                        status=msg.get('status'),
                        is_read=True,
                        date_created=msg.get('date_created')
                    )
                    message.save()
                    count += 1

                    for media in msg.get('message_media', []):
                        content_type = media.get('content_type')
                        media_url = media.get('url')

                        source_ext = mimetypes.guess_extension(content_type) or MIME_EXTENSION_MAP.get(content_type, '.bin')
                        source_file_name = create_generic_file_name(content_type, source_ext)
                        source_file_path = os.path.join(UPLOADS_URL, source_file_name)

                        download_file_from_twilio(twilio_resource=media_url, local_file_path=source_file_path)

                        if content_type.startswith("audio/"):
                            target_file_name = create_generic_file_name(content_type, '.mp3')
                            target_file_path = os.path.join(UPLOADS_URL, target_file_name)
                            target_content_type = "audio/mpeg"

                            with open(source_file_path, 'rb') as source_file:
                                buffer = convert_audio_format(file=source_file, target_file_path=target_file_path, to_format="mp3")

                            media = MessageMedia(message=message, content_type=target_content_type)
                            media.file.save(target_file_name, ContentFile(buffer.read()))

                        elif content_type.startswith("video/"):
                            target_file_name = create_generic_file_name(content_type, '.mp4')
                            target_file_path = os.path.join(UPLOADS_URL, target_file_name)

                            convert_video_to_mp4(source_file_path, target_file_path)

                            with open(target_file_path, 'rb') as target_video_file:
                                media = MessageMedia(message=message, content_type='video/mp4')
                                media.file.save(target_file_name, ContentFile(target_video_file.read()))

                        else:
                            with open(source_file_path, 'rb') as f:
                                media = MessageMedia(message=message, content_type=content_type)
                                media.file.save(source_file_name, ContentFile(f.read()))

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"❌ Failed to process message {msg.get('sid')}: {e}"))

            self.stdout.write(self.style.SUCCESS(f"✅ Successfully saved {count} messages to the database"))