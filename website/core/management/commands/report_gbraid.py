from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Event, Lead, LeadMarketingMetadata
from core.conversions import conversion_service
from marketing.utils import parse_google_ads_cookie

class Command(BaseCommand):
    help = 'Report gbraid conversions.'

    def handle(self, *args, **options):
        from django.db.models import Exists, OuterRef

        gbraid_qs = LeadMarketingMetadata.objects.filter(
            lead_marketing__lead=OuterRef("pk"),
            key="gbraid",
        )

        gclid_qs = LeadMarketingMetadata.objects.filter(
            lead_marketing__lead=OuterRef("pk"),
            key="gclid",
        )

        gcl_aw_qs = LeadMarketingMetadata.objects.filter(
            lead_marketing__lead=OuterRef("pk"),
            key="_gcl_aw",
        )

        start_date = timezone.make_aware(datetime(2026, 1, 6))

        leads = (
            Lead.objects
            .annotate(
                has_gbraid=Exists(gbraid_qs),
                has_gclid=Exists(gclid_qs),
                has_gcl_aw=Exists(gcl_aw_qs),
            )
            .filter(
                created_at__gte=start_date,
                has_gbraid=True,
                has_gclid=False,
                has_gcl_aw=False,
            )
        )

        for lead in leads:
            event_time = lead.created_at.timestamp()

            data = {
                'event_name': 'generate_lead',
                'ip_address': lead.lead_marketing.ip,
                'user_agent': lead.lead_marketing.user_agent,
                'instant_form_lead_id': lead.lead_marketing.instant_form_lead_id,
                'event_time': event_time,
                'phone_number': lead.phone_number,
                'external_id': str(lead.lead_marketing.external_id),
                'lead_id': lead.pk,
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
                elif metadata.key == '_gcl_aw':
                    if 'gclid' not in data:
                        cookie_click_id = parse_google_ads_cookie(metadata.value)
                        if cookie_click_id:
                            data['gclid'] = cookie_click_id
                else:
                    data[metadata.key] = metadata.value

            try:
                conversion_service.send_conversion(data=data)
            except Exception as e:
                print(f'Error sending conv: {e}')