from django.core.management.base import BaseCommand, CommandError

from core.conversions import conversion_service
from core.models import Event

class Command(BaseCommand):
    help = "Send a conversion event via the Google Ads conversion service using either a JSON string (--event) or file (--event_file)."

    def handle(self, *args, **options):
        try:
            events = Event.objects.all()
            for event in events:
                gclid = event.lead.lead_marketing.metadata.filter(key='gclid').first()
                if not gclid:
                    continue

                gads_service = conversion_service.get("gads")

                data = {
                    'event_name': 'event_booked',
                    'gclid': gclid,
                    'event_time': event.date_paid.timestamp(),
                    'value': event.amount,
                    'order_id': event.pk,
                }

                response = gads_service.send_conversion(data=data)
                if response:
                    print(response)
        except Exception as e:
            raise CommandError(f"❌ Failed to send Google Ads conversion: {e}")