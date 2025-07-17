import json
from django.core.management.base import BaseCommand
from django.db import transaction
from core.facebook.api import facebook_api_service
from core.models import Lead, LeadMarketing, AdCampaign, AdGroup, Ad
from marketing.enums import ConversionServiceType


class Command(BaseCommand):
    help = 'Fetch Facebook leads and either save to DB or export to JSON.'

    FIELD_MAP = {
        'full_name': ['full_name', 'nombre_completo', 'name'],
        'message': ['message', 'services', 'city', 'brief_description', 'ciudad'],
        'phone_number': ['phone_number', 'telefono'],
        'date_created': ['created_time']
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
        entries = []

        forms = facebook_api_service.get_leadgen_forms()
        for form in forms:
            form_id = form.get('id')
            leads = facebook_api_service.get_all_leads_for_form(form_id)
            for lead in leads:
                entry = self.extract_lead_data(lead)
                entries.append(entry)

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
                                    ad_group_id=entry.get('ad_group_id'),
                                    defaults={
                                        'name': entry.get('ad_group_name'),
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

    def extract_lead_data(self, lead):
        data = {
            'leadgen_id': lead.get('id'),
            'created_time': lead.get('created_time'),
            'ad_id': lead.get('ad_id'),
            'ad_name': lead.get('ad_name'),
            'ad_group_id': lead.get('adset_id'),
            'ad_group_name': lead.get('adset_name'),
            'campaign_id': lead.get('campaign_id'),
            'campaign_name': lead.get('campaign_name'),
            'platform': lead.get('platform'),
            'is_organic': lead.get('is_organic'),
            'form_id': lead.get('form_id'),
        }

        for key, possible_names in self.FIELD_MAP.items():
            data[key] = self.get_field_value(lead, possible_names)

        return data

    def get_field_value(self, lead, possible_names):
        field_data = lead.get('field_data', [])
        for name in possible_names:
            for field in field_data:
                if name.lower() in field.get('name', '').lower():
                    return field.get('values', [None])[0]
        return None