import json
from django.core.management.base import BaseCommand, CommandError

from core.facebook.api import facebook_api_service


class Command(BaseCommand):
    help = 'Fetch and print Facebook lead data for a given leadgen_id using the existing facebook_api_service instance.'

    def add_arguments(self, parser):
        parser.add_argument('--lead_id', type=str, required=True, help='Facebook Lead ID (leadgen_id)')

    def handle(self, *args, **options):
        lead_id = options['lead_id']
        if not lead_id:
            raise CommandError('--lead_id is required.')

        try:
            lead = facebook_api_service.get_lead_data(lead={'leadgen_id': lead_id})

            self.stdout.write(json.dumps(lead, indent=2))
        except Exception as e:
            raise CommandError(f'Error retrieving lead: {e}')
