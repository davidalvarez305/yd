import json
from django.core.management.base import BaseCommand
from core.calling import calling_service
from core.models import PhoneCall, User
from core.utils import cleanup_dir_files
from website import settings


class Command(BaseCommand):
    help = 'Fetch Twilio phone calls and optionally save to DB or export to JSON. Adds transcription and AI summary.'

    def add_arguments(self, parser):
        parser.add_argument('--save', action='store_true', help='Save phone calls to the database')
        parser.add_argument('--json', action='store_true', help='Export phone calls to calls.json')

    def handle(self, *args, **options):
        calls = calling_service.get_phone_calls()

        normalized_company_number = "+1" + settings.COMPANY_PHONE_NUMBER
        EXCLUDED_NUMBERS = [normalized_company_number]
        superadmins = User.objects.filter(is_superuser=True)
        for user in superadmins:
            if user.forward_phone_number:
                EXCLUDED_NUMBERS.append(user.forward_phone_number.strip())
            if user.phone_number:
                EXCLUDED_NUMBERS.append(user.phone_number.strip())

        if options['json']:
            with open('calls.json', 'w', encoding='utf-8') as f:
                json.dump(calls, f, ensure_ascii=False, indent=2)
            self.stdout.write(self.style.SUCCESS(f"✅ Exported {len(calls)} calls to calls.json"))

        if options['save']:
            saved = 0

            for call in calls:
                try:
                    if not isinstance(call, dict):
                        self.stderr.write(self.style.WARNING(f"⚠️ Skipping non-dict call: {call}"))
                        continue

                    is_inbound = call.get("direction") != "outbound-api"

                    if is_inbound:
                        # Inbound call: look for first audio recording
                        recording_url = ""
                        for recording in call.get("call_recordings", []):
                            if not isinstance(recording, dict):
                                self.stderr.write(self.style.WARNING(f"⚠️ Skipping invalid recording: {recording}"))
                                continue
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
                                "is_inbound": True,
                                "date_created": call.get('date_created'),
                            },
                        )
                        if created:
                            saved += 1

                    else:
                        # Outbound: process child calls
                        for child in call.get("child_calls", []):
                            if not isinstance(child, dict):
                                self.stderr.write(self.style.WARNING(f"⚠️ Skipping invalid child call: {child}"))
                                continue

                            to_number = (child.get("to") or "").strip()
                            if to_number in EXCLUDED_NUMBERS:
                                continue

                            child_recording_url = ""
                            for recording in child.get("call_recordings", []):
                                if not isinstance(recording, dict):
                                    self.stderr.write(self.style.WARNING(f"⚠️ Skipping invalid child recording: {recording}"))
                                    continue
                                if recording.get("url") and recording.get("content_type", "").startswith("audio/"):
                                    child_recording_url = recording["url"]
                                    break

                            child_call, child_created = PhoneCall.objects.get_or_create(
                                external_id=child.get("sid"),
                                defaults={
                                    "call_from": child.get("from"),
                                    "call_to": child.get("to"),
                                    "call_duration": int(child.get("duration") or 0),
                                    "status": child.get("status"),
                                    "recording_url": child_recording_url,
                                    "is_inbound": False,
                                    "date_created": child.get("date_created"),
                                },
                            )
                            if child_created:
                                saved += 1

                except Exception as e:
                    sid = call.get("sid") if isinstance(call, dict) else "<unknown>"
                    self.stderr.write(self.style.ERROR(f"❌ Failed on call {sid}: {e}"))

                finally:
                    cleanup_dir_files(settings.UPLOADS_URL)

            self.stdout.write(self.style.SUCCESS(f"✅ Saved {saved} calls to DB"))