import json
from django.core.management.base import BaseCommand
from core.calling import calling_service
from core.models import PhoneCall, PhoneCallTranscription, User
from core.utils import cleanup_dir_files
from website import settings


class Command(BaseCommand):
    help = 'Fetch Twilio phone calls and optionally save to DB or export to JSON. Adds transcription and AI summary.'

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

        for call in calls:
            if not isinstance(call, dict):
                self.stderr.write(self.style.WARNING(f"⚠️ Skipping non-dict call object: {call}"))
                continue

            try:
                is_inbound = call.get("direction") != "outbound-api"

                if is_inbound:
                    recording = call.get('recording')
                    phone_call, created = PhoneCall.objects.update_or_create(
                        external_id=call.get("sid"),
                        defaults={
                            "call_from": call.get("from"),
                            "call_to": call.get("to"),
                            "call_duration": int(call.get("duration") or 0),
                            "status": call.get("status"),
                            "is_inbound": True,
                            "date_created": call.get("date_created"),
                        },
                    )

                    if not created:
                        phone_call.date_created = call.get("date_created")
                        phone_call.save()

                    transcriptions = PhoneCallTranscription.objects.filter(phone_call=phone_call)
                    if transcriptions.count() == 0 and recording and phone_call.duration > 30:
                        calling_service.download_call_recording(recording.sid, phone_call.external_id)

                else:
                    child_calls = call.get("child_calls", [])
                    if not isinstance(child_calls, list):
                        continue

                    for call in child_calls:
                        if not isinstance(call, dict):
                            continue

                        to_number = (call.get("to") or "").strip()
                        if to_number in EXCLUDED_NUMBERS:
                            continue

                        recording = call.get('recording')
                        child_call, child_created = PhoneCall.objects.update_or_create(
                            external_id=call.get("sid"),
                            defaults={
                                "call_from": call.get("from"),
                                "call_to": call.get("to"),
                                "call_duration": int(call.get("duration") or 0),
                                "status": call.get("status"),
                                "is_inbound": False,
                                "date_created": call.get("date_created"),
                            },
                        )

                        if not child_created:
                            child_call.date_created = call.get("date_created")
                            child_call.save()

                        transcriptions = PhoneCallTranscription.objects.filter(phone_call=child_call)
                        if transcriptions.count() == 0 and recording and child_call.duration > 30:
                            calling_service.download_call_recording(recording.sid, child_call.external_id)

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Failed on call {call.get('sid', 'unknown')}: {e}"))

            finally:
                cleanup_dir_files(settings.UPLOADS_URL)