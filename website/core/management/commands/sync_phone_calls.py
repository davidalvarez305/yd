import json

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware

from core.messaging import messaging_service
from core.models import PhoneCall
from core.utils import strip_country_code, cleanup_dir_files
from website.settings import UPLOADS_URL

class Command(BaseCommand):
    help = 'Fetch Twilio phone calls and optionally save to DB or export to JSON. Adds transcription and AI summary.'

    def add_arguments(self, parser):
        parser.add_argument('--save', action='store_true', help='Save phone calls to the database')
        parser.add_argument('--json', action='store_true', help='Export phone calls to calls.json')

    def handle(self, *args, **options):
        calls = messaging_service.get_all_calls()

        if options['json']:
            with open('calls.json', 'w', encoding='utf-8') as f:
                json.dump(calls, f, ensure_ascii=False, indent=2)
            self.stdout.write(self.style.SUCCESS(f"✅ Exported {len(calls)} calls to calls.json"))

        if options['save']:
            saved = 0
            for call in calls:
                try:
                    sid = call.get("sid")
                    from_number = strip_country_code(call.get("from", ""))
                    to_number = strip_country_code(call.get("to", ""))
                    status = call.get("status")
                    duration = int(call.get("duration") or 0)
                    is_inbound = call.get("direction") != "outbound-api"
                    created = make_aware(call["date_created"]) if call.get("date_created") else None

                    recording_url = ""
                    for recording in call.get("call_recordings", []):
                        if recording.get("url") and recording.get("content_type", "").startswith("audio/"):
                            recording_url = recording["url"]
                            break

                    phone_call, created = PhoneCall.objects.get_or_create(
                        external_id=sid,
                        defaults={
                            "call_from": from_number,
                            "call_to": to_number,
                            "call_duration": duration,
                            "status": status,
                            "recording_url": recording_url,
                            "is_inbound": is_inbound,
                            "date_created": created,
                        },
                    )

                    if created:
                        saved += 1

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"❌ Failed on call {call.get('sid')}: {e}"))

                finally:
                    cleanup_dir_files(UPLOADS_URL)

            self.stdout.write(self.style.SUCCESS(f"✅ Saved {saved} calls to DB"))