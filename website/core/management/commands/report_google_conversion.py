import json
import os
from django.core.management.base import BaseCommand, CommandError
from core.conversions import conversion_service
from website import settings

class Command(BaseCommand):
    help = "Send a conversion event via the Google Ads conversion service using either a JSON string (--event) or file (--event_file)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--event",
            type=str,
            help="JSON string representing the event data (e.g., '{\"event_name\": \"generate_lead\", \"email\": \"test@example.com\"}').",
        )
        parser.add_argument(
            "--event_file",
            type=str,
            help="Path to a JSON file containing the event data (e.g., './event.json').",
        )

    def handle(self, *args, **options):
        event = options.get("event")
        event_file = os.path.join(settings.PROJECT_ROOT, options.get("event_file"))

        if not event and not event_file:
            raise CommandError("❌ You must provide either --event or --event_file.")

        if event_file:
            if not os.path.exists(event_file):
                raise CommandError(f"❌ Event file not found: {event_file}")
            try:
                with open(event_file, "r", encoding="utf-8") as f:
                    event_data = json.load(f)
            except Exception as e:
                raise CommandError(f"❌ Failed to load event file '{event_file}': {e}")
        else:
            try:
                event_data = json.loads(event)
            except json.JSONDecodeError as e:
                raise CommandError(f"❌ Invalid JSON string passed to --event: {e}")

        if "event_name" not in event_data and "action" not in event_data:
            raise CommandError("❌ Missing required key: either 'event_name' or 'action' must be present in event data.")

        try:
            gads_service = conversion_service.get("gads")
            response = gads_service.send_conversion(event_data)
            if response:
                print(response)
        except Exception as e:
            raise CommandError(f"❌ Failed to send Google Ads conversion: {e}")