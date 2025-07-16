import json
import requests
from django.core.management.base import BaseCommand, CommandError
from website import settings


class Command(BaseCommand):
    help = 'Fetch and save Facebook leads data to a JSON file with pagination support.'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default='leads_data.json', help='Output file path')

    def handle(self, *args, **options):
        output_file = options.get('output')
        all_leads = []

        forms = self.get_leadgen_forms()

        for form in forms:
            form_id = form.get('id')
            leads = self.get_all_leads_for_form(form_id)
            for lead in leads:
                lead_data = self.extract_lead_data(lead)
                all_leads.append(lead_data)

        with open(output_file, 'w') as f:
            json.dump(all_leads, f, indent=2)

        self.stdout.write(self.style.SUCCESS(f'✅ Successfully saved {len(all_leads)} leads to {output_file}'))

    def get_leadgen_forms(self):
        url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{settings.FACEBOOK_PAGE_ID}"
        params = {
            'access_token': settings.FACEBOOK_PAGE_ACCESS_TOKEN,
            'fields': 'leadgen_forms{id}',
        }

        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise CommandError(f"Error fetching leadgen_forms: {response.json()}")

        data = response.json()
        return data.get('leadgen_forms', {}).get('data', [])

    def get_all_leads_for_form(self, form_id):
        leads = []
        url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{form_id}/leads"
        params = {
            'access_token': settings.FACEBOOK_PAGE_ACCESS_TOKEN,
            'fields': 'field_data,ad_id,ad_name,adset_id,adset_name,campaign_id,campaign_name,created_time,form_id,id,partner_name,platform,is_organic',
            'limit': 100,
        }

        while url:
            response = requests.get(url, params=params)
            if response.status_code != 200:
                raise CommandError(f"Error fetching leads for form {form_id}: {response.json()}")

            data = response.json()
            leads.extend(data.get('data', []))
            url = data.get('paging', {}).get('next')
            params = {}

        return leads

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