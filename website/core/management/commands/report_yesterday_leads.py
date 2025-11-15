from datetime import timedelta, timezone
from django.core.management.base import BaseCommand, CommandError
from core.conversions import conversion_service
from core.models import Lead
from website import settings

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

            yesterday = timezone.now().date() - timedelta(days=1)
            leads = Lead.objects.filter(created_at__date=yesterday)
            
            for lead in leads:
                data = {
                    'event_name': 'generate_lead',
                    'ip_address': lead.lead_marketing.ip,
                    'user_agent': lead.lead_marketing.user_agent,
                    'instant_form_lead_id': lead.lead_marketing.instant_form_lead_id,
                    'event_time': lead.created_at.timestamp(),
                    'phone_number': lead.phone_number,
                    'external_id': str(lead.lead_marketing.external_id)
                }

            for metadata in lead.lead_marketing.metadata.all():
                if metadata.key == '_fbc':
                    data['fbc'] = metadata.value
                elif metadata.key == '_fbp':
                    data['fbp'] = metadata.value
                elif metadata.key == '_ga':
                    data['ga'] = metadata.value
                elif metadata.key == 'gclid':
                    data['gclid'] = metadata.value
                elif metadata.key == 'gbraid':
                    data['gbraid'] = metadata.value
                elif metadata.key == 'wbraid':
                    data['wbraid'] = metadata.value
                else:
                    data[metadata.key] = metadata.value

                if dry_run:
                    print(f"Dry-run: For lead: {lead.full_name}")
                else:
                    try:
                        conversion_service.send_conversion(data=data)
                    except BaseException as e:
                        continue
        except Exception as e:
            raise CommandError(f"❌ Failed to send Google Ads conversion: {e}")