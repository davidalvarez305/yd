import json
from dateutil import parser
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Lead, Event
from core.utils import normalize_phone_number

class Command(BaseCommand):
    help = 'Import enriched events from a JSON file and either save to DB or export to data.json.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to JSON file with enriched event data'
        )
        parser.add_argument(
            '--save',
            action='store_true',
            help='Save events to the database'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Export parsed events to load.json'
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])

        if not file_path.exists():
            self.stderr.write(self.style.ERROR(f"❌ File not found: {file_path}"))
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                events = json.load(f)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Failed to load JSON: {e}"))
            return

        if not isinstance(events, list):
            self.stderr.write(self.style.ERROR("❌ Expected a list of event objects in the JSON file."))
            return

        entries = []
        for event in events:
            try:
                entries.append(self.extract_entry(event))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'❌ Failed to extract event {event}: {e}'))
                continue

        if options['json']:
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
            self.stdout.write(self.style.SUCCESS(f"✅ Exported {len(entries)} events to load.json"))

        if options['save']:
            count = 0
            for entry in entries:
                try:
                    with transaction.atomic():
                        lead = Lead.objects.filter(phone_number=normalize_phone_number(entry.get('phone_number'))).first()
                        if not lead:
                            continue

                        instance = Event.objects.create(
                            lead=lead,
                            street_address=entry.get('street_address'),
                            city=entry.get('city'),
                            zip_code=entry.get('zip_code'),
                            start_time=entry.get('start_time'),
                            date_created=entry.get('date_created'),
                            end_time=entry.get('end_time'),
                            amount=entry.get('amount'),
                            tip=entry.get('tip'),
                            guests=entry.get('guests'),
                        )

                        count += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"❌ Failed to save event {entry['event_id']}: {e}"))

            self.stdout.write(self.style.SUCCESS(f"✅ Successfully saved {count} new events to the database"))

    def extract_entry(self, raw):
        """Normalize JSON fields into Event fields"""

        # amount might look like "$1,480.00"
        amount = raw.get("amount")
        if amount:
            amount = float(amount.replace("$", "").replace(",", ""))

        # tip might look like "$120.00"
        tip = raw.get("tip")
        if tip:
            tip = float(tip.replace("$", "").replace(",", ""))

        return {
            "event_id": raw.get("event_id"),
            "lead_id": raw.get("lead_id"),
            "street_address": raw.get("street_address"),
            "city": raw.get("city"),
            "zip_code": raw.get("zip_code"),
            "start_time": self.parse_datetime(raw.get("start_time")),
            "end_time": self.parse_datetime(raw.get("end_time")),
            "date_created": self.parse_datetime(raw.get("date_created")),
            "amount": amount,
            "tip": tip,
            "guests": raw.get("guests"),
            "phone_number": raw.get("phone_number"),
        }

    def parse_datetime(self, value):
        if not value:
            return None
        try:
            return parser.isoparse(value)
        except (ValueError, TypeError):
            self.stderr.write(self.style.WARNING(f"⚠️ Invalid datetime format: {value}"))
            return None