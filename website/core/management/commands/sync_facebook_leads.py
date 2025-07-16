import json
import requests
from django.core.management.base import BaseCommand, CommandError
from website import settings

LEAD_FORM_IDS = [
    3903866236536472,
    29878073318450475,
    1435970247541928,
    1980870116054110,
]

class Command(BaseCommand):
    help = 'Fetch and save Facebook leads data to a JSON file without enriching it'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default='leads_data.json', help='Output file path')

    def handle(self, *args, **options):
        output_file = options.get('output')
        all_leads = []

        for form_id in LEAD_FORM_IDS:
            self.stdout.write(f'📥 Fetching leads from form: {form_id}')
            leads = self.get_leads(form_id)

            for lead in leads:
                lead_data = self.extract_lead_data(lead)
                all_leads.append(lead_data)

        with open(output_file, 'w') as f:
            json.dump(all_leads, f, indent=2)

        self.stdout.write(self.style.SUCCESS(f'✅ Successfully saved {len(all_leads)} leads to {output_file}'))

    def get_leads(self, form_id):
        url = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}/{form_id}/leads"
        params = {
            'access_token': settings.FACEBOOK_PAGE_ACCESS_TOKEN,
            'limit': 100,
        }
        leads = []

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
        }
        return lead_data

    def get_field_value(self, lead, field_name):
        for field in lead.get('field_data', []):
            if field_name in field.get('name'):
                return field.get('values', [None])[0]
        return None