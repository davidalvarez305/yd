from django.core.management.base import BaseCommand, CommandError

from core.models import Lead, LeadMarketingMetadata
from marketing.enums import MarketingParams

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            leads = Lead.objects.all()

            for lead in leads:
                landing_page = getattr(lead.lead_marketing, 'landing_page', None)

                if not landing_page:
                    continue

                metadata = {}

                if 'fbclid' in landing_page:
                    metadata.update({
                        'fbc': getattr(lead.lead_marketing, 'click_id', None),
                        'fbp': getattr(lead.lead_marketing, 'client_id', None),
                    })
                
                for key in MarketingParams.GoogleURLClickIDKeys.value:
                    if key in landing_page:
                        metadata.update({
                            key: getattr(lead.lead_marketing, 'click_id', None),
                            'ga': getattr(lead.lead_marketing, 'client_id', None),
                        })

                metadata.update({
                    'source': getattr(lead.lead_marketing, 'source', None),
                    'medium': getattr(lead.lead_marketing, 'medium', None),
                    'channel': getattr(lead.lead_marketing, 'channel', None),
                    'landing_page': getattr(lead.lead_marketing, 'landing_page', None),
                    'keyword': getattr(lead.lead_marketing, 'keyword', None)
                })

                for key, value in metadata.items():
                    if value:
                        metadata_entry, _ = LeadMarketingMetadata.objects.get_or_create(
                            key=key,
                            value=value,
                            lead_marketing=lead.lead_marketing
                        )

        except Exception as e:
            raise CommandError(f'Error retrieving unread messages: {e}')