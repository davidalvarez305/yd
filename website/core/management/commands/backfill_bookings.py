from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from core.conversions import conversion_service
from core.models import Event

class Command(BaseCommand):
    help = "Send a conversion event via the Google Ads conversion service using either a JSON string (--event) or file (--event_file)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only print the conversion data, do not send to Google Ads',
        )

    def handle(self, *args, **options):
        try:
            dry_run = options.get('dry_run', False)
            events = Event.objects.filter(date_created__gte=datetime(2025, 10, 1))
            
            for event in events:
                lead_marketing = getattr(event.lead, "lead_marketing", None)
                if not lead_marketing:
                    continue

                gclid = lead_marketing.metadata.filter(key='gclid').first()
                if not gclid:
                    continue

                data = {
                    'event_name': 'event_booked',
                    'gclid': gclid.value,
                    'event_time': event.date_paid.timestamp(),
                    'value': event.amount,
                    'order_id': event.pk,
                }

                if dry_run:
                    print(f"Dry-run: For lead: {event.lead.full_name} - event: {event.pk} - value: {event.amount}")
                    print("Data that would be sent:", data)
                else:
                    gads_service = conversion_service.get("gads")
                    response = gads_service.send_conversion(data=data)
                    if response:
                        print(response)

        except Exception as e:
            raise CommandError(f"❌ Failed to send Google Ads conversion: {e}")