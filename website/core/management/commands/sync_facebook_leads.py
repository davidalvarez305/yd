import json
from dateutil import parser

from django.core.management.base import BaseCommand
from django.db import transaction

from core.facebook.api import facebook_api_service
from core.models import Lead, LeadMarketing, AdCampaign, AdGroup, Ad
from marketing.enums import ConversionServiceType
from core.utils import normalize_phone_number
from website.marketing.utils import get_facebook_form_values


class Command(BaseCommand):
    help = 'Fetch Facebook leads and either save to DB or export to JSON.'

    FIELD_MAP = {
        'full_name': ['full_name', 'nombre_completo', 'name'],
        'message': ['message', 'services', 'city', 'brief_description', 'ciudad'],
        'phone_number': ['phone_number', 'telefono']
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--save',
            action='store_true',
            help='Save leads to the database'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Export leads to data.json'
        )

    def handle(self, *args, **options):
        self.options = options
        entries = []

        forms = facebook_api_service.get_leadgen_forms()
        for form in forms:
            form_id = form.get('id')
            leads = facebook_api_service.get_all_leads_for_form(form_id)
            for lead in leads:
                entries.append(get_facebook_form_values(lead, options['save']))

        if options['json']:
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
            self.stdout.write(self.style.SUCCESS(f"✅ Exported {len(entries)} leads to data.json"))

        if options['save']:
            count = 0
            for entry in entries:
                if 'test lead' in entry.get('full_name'):
                    continue
                try:
                    with transaction.atomic():
                        lead, created = Lead.objects.get_or_create(
                            phone_number=entry.get('phone_number'),
                            defaults={
                                'full_name': entry.get('full_name'),
                                'message': entry.get('message'),
                                'created_at': entry.get('created_time'),
                            }
                        )

                        if created:
                            marketing, _ = LeadMarketing.objects.get_or_create(
                                instant_form_lead_id=entry.get('leadgen_id'),
                                defaults={
                                    'lead': lead,
                                    'source': entry.get('platform'),
                                    'medium': 'paid',
                                    'channel': 'social',
                                    'instant_form_id': entry.get('form_id'),
                                }
                            )

                            if not entry.get('is_organic'):
                                ad_campaign, _ = AdCampaign.objects.get_or_create(
                                    ad_campaign_id=entry.get('campaign_id'),
                                    defaults={'name': entry.get('campaign_name')}
                                )
                                ad_group, _ = AdGroup.objects.get_or_create(
                                    ad_group_id=entry.get('adset_id'),
                                    defaults={
                                        'name': entry.get('adset_name'),
                                        'ad_campaign': ad_campaign,
                                    }
                                )
                                ad, _ = Ad.objects.get_or_create(
                                    ad_id=entry.get('ad_id'),
                                    defaults={
                                        'name': entry.get('ad_name'),
                                        'platform_id': ConversionServiceType.FACEBOOK.value,
                                        'ad_group': ad_group,
                                    }
                                )
                                marketing.ad = ad
                                marketing.save()
                            count += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"❌ Failed to process lead {entry.get('leadgen_id')}: {e}"))

            self.stdout.write(self.style.SUCCESS(f"✅ Successfully saved {count} new leads to the database"))