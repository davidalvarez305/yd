from django.core.management.base import BaseCommand
from django.db import transaction
from core.facebook.api import facebook_api_service
from core.models import Lead, LeadMarketing, AdCampaign, AdGroup, Ad
from marketing.enums import ConversionServiceType

class Command(BaseCommand):
    help = 'Fetch and save Facebook leads data to a JSON file with pagination support.'

    def handle(self, *args, **options):
        all_leads = []

        forms = facebook_api_service.get_leadgen_forms()

        for form in forms:
            form_id = form.get('id')
            leads = facebook_api_service.get_all_leads_for_form(form_id)
            for lead in leads:
                lead_data = self.extract_lead_data(lead)
                all_leads.append(lead_data)

        for entry in all_leads:
            try:
                data = facebook_api_service.get_lead_data(lead=entry)

                with transaction.atomic():
                    lead, created = Lead.objects.get_or_create(
                        phone_number=data.get('phone_number'),
                        defaults={
                            'full_name': data.get('full_name'),
                            'message': data.get('city'),
                        }
                    )

                    if created:
                        marketing, _ = LeadMarketing.objects.get_or_create(
                            instant_form_lead_id=entry.get('id'),
                            defaults={
                                'lead': lead,
                                'source': data.get('platform'),
                                'medium': 'paid',
                                'channel': 'social',
                                'instant_form_id': data.get('form_id'),
                            }
                        )

                        if not data.get('is_organic'):
                            ad_campaign, _ = AdCampaign.objects.get_or_create(
                                ad_campaign_id=data.get('campaign_id'),
                                defaults={'name': data.get('campaign_name')}
                            )
                            ad_group, _ = AdGroup.objects.get_or_create(
                                ad_group_id=data.get('adset_id'),
                                defaults={
                                    'name': data.get('adset_name'),
                                    'ad_campaign': ad_campaign,
                                }
                            )
                            ad, _ = Ad.objects.get_or_create(
                                ad_id=data.get('ad_id'),
                                defaults={
                                    'name': data.get('ad_name'),
                                    'platform_id': ConversionServiceType.FACEBOOK.value,
                                    'ad_group': ad_group,
                                }
                            )
                            marketing.ad = ad
                            marketing.save()

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Failed to process lead {entry.get('id')}: {e}"))

        self.stdout.write(self.style.SUCCESS(f'✅ Successfully saved {len(all_leads)} leads to data.json'))

    def extract_lead_data(self, lead):
        lead_data = {
            'leadgen_id': lead.get('id'),
            'created_time': lead.get('created_time'),
            'email': self.get_field_value(lead, 'email'),
            'full_name': self.get_field_value(lead, 'full_name'),
            'city': self.get_field_value(lead, 'city'),
            'message': self.get_field_value(lead, 'message'),
            'phone_number': self.get_field_value(lead, 'phone_number') or self.get_field_value(lead, 'telefono'),
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
        return lead_data

    def get_field_value(self, lead, field_name):
        for field in lead.get('field_data', []):
            if field.get('name') in field_name:
                return field.get('values', [None])[0]
        return None