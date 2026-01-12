from django.core.management.base import BaseCommand, CommandError
from core.conversions import conversion_service
from core.models import Lead

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

            leads = [ 4472, 4465, 4459, 4454, 4412 ]

            for pk in leads:
                lead = Lead.objects.get(pk=pk)
                gclid = lead.lead_marketing.metadata.filter(key='gclid').first()
                if not gclid:
                    continue

                data = {
                    'event_name': 'generate_lead',
                    'lead_id': lead.pk,
                    'external_id': str(lead.lead_marketing.external_id),
                    'phone_number': lead.phone_number,
                    'ip_address': lead.lead_marketing.ip,
                    'user_agent': lead.lead_marketing.user_agent,
                    'event_time': lead.created_at.timestamp()
                }

                for metadata in lead.lead_marketing.metadata.all():
                    data[metadata.key] = metadata.value

                conversion_service.retract_conversion(data=data)

        except Exception as e:
            raise CommandError(f"❌ Failed to send Google Ads conversion: {e}")