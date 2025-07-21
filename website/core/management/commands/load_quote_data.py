import json
import os

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from core.models import ServiceType, UnitType, Service, Quote, QuoteService, Lead
from website import settings
from crm.utils import update_quote_invoices
from core.utils import normalize_phone_number, parse_money

class Command(BaseCommand):
    help = 'Load and insert data into the database in the correct order without mutating data.'

    def handle(self, *args, **options):
        base_dir = settings.PROJECT_ROOT

        file_model_map = {
            'service_types.json': {
                'model': ServiceType,
                'map': {},
                'pk': 'service_type_id',
                'fields': lambda e, m: {
                    'service_type_id': e['service_type_id'],
                    'type': e['service_type']
                },
            },
            'units.json': {
                'model': UnitType,
                'map': {},
                'pk': 'unit_type_id',
                'fields': lambda e, m: {
                    'unit_type_id': e['unit_type_id'],
                    'type': e['type']
                },
            },
            'services.json': {
                'model': Service,
                'map': {},
                'pk': 'service_id',
                'fields': lambda e, m: {
                    'service_id': e['service_id'],
                    'service_type': file_model_map['service_types.json']['map'].get(e['service_type_id']),
                    'unit_type': file_model_map['units.json']['map'].get(e['unit_type_id']),
                    'service': e['service'],
                    'suggested_price': parse_money(e['suggested_price']),
                    'guest_ratio': e['guest_ratio'],
                },
            },
        }

        # Load JSON files
        for filename in file_model_map:
            path = os.path.join(base_dir, filename)
            if not os.path.exists(path):
                self.stderr.write(self.style.ERROR(f'❌ File not found: {filename}'))
                continue

            try:
                with open(path, 'r', encoding='utf-8') as f:
                    file_model_map[filename]['data'] = json.load(f)
                    self.stdout.write(self.style.SUCCESS(
                        f'✅ Loaded {len(file_model_map[filename]["data"])} from {filename}'
                    ))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'❌ Failed to load {filename}: {e}'))

        for filename, config in file_model_map.items():
            model = config['model']
            data = config.get('data', [])
            mapper = config['map']
            pk_field = config['pk']
            build_fields = config['fields']

            for entry in data:
                obj = model.objects.create(**build_fields(entry, file_model_map))
                mapper[entry[pk_field]] = obj

        # Handle quotes
        quote_map = {}
        quote_data = self.load_json('quote.json')
        for entry in quote_data:
            phone_number = normalize_phone_number(entry.get('phone_number'))
            if not phone_number:
                continue

            lead = Lead.objects.filter(phone_number=phone_number).first()
            if not lead:
                continue
            
            quote = Quote.objects.create(
                quote_id=entry.get('quote_id'),
                lead=lead,
                guests=entry.get('guests'),
                hours=entry.get('hours'),
                event_date=parse_datetime(entry.get('event_date')),
                external_id=entry.get('external_id'),
            )
            quote_map[entry['quote_id']] = quote

        # Handle quote services
        quote_services = self.load_json('quote_services.json')
        for entry in quote_services:
            quote = quote_map.get(entry['quote_id'])
            service = file_model_map['services.json']['map'].get(entry['service_id'])

            if not quote:
                continue

            if not service:
                continue

            QuoteService.objects.create(
                quote_service_id=entry.get('quote_service_id'),
                quote=quote,
                service=service,
                units=entry.get('units'),
                price_per_unit=parse_money(entry.get('price_per_unit')),
            )
        
        for entry in quote_data:
            quote = quote_map.get(entry['quote_id'])
            if quote:
                update_quote_invoices(quote=quote)

        self.stdout.write(self.style.SUCCESS('🎉 All data loaded successfully.'))

    def load_json(self, filename):
        path = os.path.join(settings.PROJECT_ROOT, filename)
        if not os.path.exists(path):
            self.stderr.write(self.style.ERROR(f'❌ File not found: {filename}'))
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Failed to load {filename}: {e}'))
            return []