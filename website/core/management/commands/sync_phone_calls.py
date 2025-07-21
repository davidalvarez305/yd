import json

from django.core.management.base import BaseCommand

from core.calling import calling_service
from core.models import PhoneCall
from core.utils import cleanup_dir_files
from website.settings import UPLOADS_URL

class Command(BaseCommand):
    help = 'Fetch Twilio phone calls and optionally save to DB or export to JSON. Adds transcription and AI summary.'

    def add_arguments(self, parser):
        parser.add_argument('--save', action='store_true', help='Save phone calls to the database')
        parser.add_argument('--json', action='store_true', help='Export phone calls to calls.json')

    def handle(self, *args, **options):
        calls = calling_service.get_phone_calls()

        if options['json']:
            with open('calls.json', 'w', encoding='utf-8') as f:
                json.dump(calls, f, ensure_ascii=False, indent=2)
            self.stdout.write(self.style.SUCCESS(f"✅ Exported {len(calls)} calls to calls.json"))

        if options['save']:
            saved = 0
            for call in calls:
                try:
                    recording_url = ""
                    for recording in call.get("call_recordings", []):
                        if recording.get("url") and recording.get("content_type", "").startswith("audio/"):
                            recording_url = recording["url"]
                            break

                    phone_call, created = PhoneCall.objects.get_or_create(
                        external_id=call.get("sid"),
                        defaults={
                            "call_from": call.get('from'),
                            "call_to": call.get("to"),
                            "call_duration": int(call.get("duration") or 0),
                            "status": call.get("status"),
                            "recording_url": recording_url,
                            "is_inbound": call.get("direction") != "outbound-api",
                            "date_created": call.get('date_created'),
                        },
                    )

                    if created:
                        saved += 1

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"❌ Failed on call {call.get('sid')}: {e}"))

                finally:
                    cleanup_dir_files(UPLOADS_URL)

            self.stdout.write(self.style.SUCCESS(f"✅ Saved {saved} calls to DB"))