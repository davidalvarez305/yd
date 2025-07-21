import json
import os

from django.core.management.base import BaseCommand
from crm.models import ServiceType, UnitType, Service, Quote, QuoteService, Lead
from website import settings

class Command(BaseCommand):
    help = 'Load and insert data into the database in the correct order without mutating data.'

    def handle(self, *args, **options):
        base_dir = settings.UPLOAD_URL

        file_map = {
            'service_types.json': [],
            'units.json': [],
            'services.json': [],
            'quote.json': [],
            'quote_services.json': [],
        }

        for filename in file_map:
            path = os.path.join(base_dir, filename)
            if not path.exists():
                self.stderr.write(self.style.ERROR(f'❌ File not found: {filename}'))
                continue
            try:
                with path.open('r', encoding='utf-8') as f:
                    file_map[filename] = json.load(f)
                    self.stdout.write(self.style.SUCCESS(f'✅ Loaded {len(file_map[filename])} from {filename}'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'❌ Failed to load {filename}: {e}'))

        service_type_map = {}
        unit_type_map = {}
        service_map = {}
        quote_map = {}

        for entry in file_map['service_types.json']:
            obj = ServiceType.objects.create(
                service_type_id=entry['service_type_id'],
                service_type=entry['service_type']
            )
            service_type_map[entry['service_type_id']] = obj

        for entry in file_map['units.json']:
            obj = UnitType.objects.create(
                unit_type_id=entry['unit_type_id'],
                unit_type=entry['unit_type']
            )
            unit_type_map[entry['unit_type_id']] = obj

        for entry in file_map['services.json']:
            service_type = service_type_map.get(entry['service_type_id'])
            unit_type = unit_type_map.get(entry['unit_type_id'])

            obj = Service.objects.create(
                service_id=entry['service_id'],
                name=entry['name'],
                price=entry['price'],
                service_type=service_type,
                unit_type=unit_type,
                # add any additional fields here
            )
            service_map[entry['service_id']] = obj

        # Insert Quotes
        for entry in file_map['quote.json']:
            lead_id = entry['lead_id']
            try:
                lead = Lead.objects.get(pk=lead_id)
            except Lead.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'❌ Lead with ID {lead_id} not found. Skipping quote ID {entry.get("quote_id")}'))
                continue

            obj = Quote.objects.create(
                quote_id=entry['quote_id'],
                lead=lead,
                # other fields here...
            )
            quote_map[entry['quote_id']] = obj

        # Insert QuoteServices
        for entry in file_map['quote_services.json']:
            quote = quote_map.get(entry['quote_id'])
            service = service_map.get(entry['service_id'])

            if not quote or not service:
                self.stderr.write(self.style.ERROR(f'❌ Missing quote or service for QuoteService {entry.get("quote_service_id")}'))
                continue

            QuoteService.objects.create(
                quote_service_id=entry['quote_service_id'],
                quote=quote,
                service=service,
                quantity=entry.get('quantity', 1),
                # add more fields here if necessary
            )

        self.stdout.write(self.style.SUCCESS('🎉 All data loaded successfully.'))