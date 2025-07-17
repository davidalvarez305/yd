import os
import json
from dateutil import parser

from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from core.models import Lead, LeadMarketing, AdCampaign, AdGroup, Ad
from core.google.api import google_api_service
from marketing.enums import ConversionServiceType

CREDENTIALS_PATH = os.path.join(settings.PROJECT_ROOT, 'credentials.json')
TOKEN_PATH = os.path.join(settings.PROJECT_ROOT, 'token.json')

class Command(BaseCommand):
    help = 'Import leads from Google Sheets API (no gspread) and save/export them.'

    SHEET_FIELD_MAP = {
        "Old Form": {
            "full_name": ["what's_your_full_name?"],
            "phone_number": ["what's_the_best_phone_number_to_reach_you_at?"],
            "message": ["give_us_a_brief_description_of_your_event"],
            "email": ["email"],
        },
        "Old Form2": {
            "full_name": ["full name"],
            "phone_number": ["phone_number"],
            "email": ["email"],
            "message": [],
        },
        "Old Form3": {
            "full_name": ["nombre_completo"],
            "phone_number": ["número_de_telefono"],
            "city": ["ciudad"],
            "email": ["correo_electrónico"],
            "message": [],
        },
    }

    def add_arguments(self, parser):
        parser.add_argument('--sheet_id', required=True, help='Google Sheet ID')
        parser.add_argument('--json', action='store_true', help='Export to data.json')
        parser.add_argument('--save', action='store_true', help='Save to database')

    def parse_datetime(self, value):
        if not value:
            return None
        try:
            return parser.isoparse(value)
        except (ValueError, TypeError):
            self.stderr.write(self.style.WARNING(f"⚠️ Invalid datetime format: {value}"))
            return None

    def handle(self, *args, **options):
        sheet_id = options['sheet_id']

        all_entries = []

        for sheet_name, field_map in self.SHEET_FIELD_MAP.items():
            try:
                rows = google_api_service.get_sheet_data(
                    spreadsheetId=sheet_id,
                    range=f"{sheet_name}!A1:Z"
                )

                for row in rows:
                    all_entries.append(self.extract_lead_data(row, field_map))

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Failed to read sheet {sheet_name}: {e}"))

        if options['json']:
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(all_entries, f, ensure_ascii=False, indent=2)
            self.stdout.write(self.style.SUCCESS(f"✅ Exported {len(all_entries)} leads to data.json"))

        if options['save']:
            self.save_to_database(all_entries)

    def save_to_database(self, entries):
        count = 0
        for entry in entries:
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
                            instant_form_lead_id=entry.get('id'),
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
                self.stderr.write(self.style.ERROR(f"❌ Failed to save lead {entry.get('id')}: {e}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Saved {count} new leads to the database"))

    def extract_lead_data(self, row, field_map):
        def strip_prefix(value):
            """Strip prefix before colon in IDs like 'l:2034' => '2034'."""
            if isinstance(value, str) and ':' in value:
                return value.split(':', 1)[1]
            return value

        data = {
            'id': strip_prefix(row.get('id')),
            'created_time': self.parse_datetime(row.get('created_time')),
            'ad_id': strip_prefix(row.get('ad_id')),
            'ad_name': row.get('ad_name'),
            'ad_group_id': strip_prefix(row.get('ad_group_id') or row.get('adset_id')),  # allow either key
            'ad_group_name': row.get('ad_group_name') or row.get('adset_name'),
            'campaign_id': strip_prefix(row.get('campaign_id')),
            'campaign_name': row.get('campaign_name'),
            'form_id': strip_prefix(row.get('form_id')),
            'form_name': row.get('form_name'),
            'is_organic': row.get('is_organic'),
            'platform': row.get('platform'),
            'is_qualified': row.get('is_qualified'),
            'is_quality': row.get('is_quality'),
            'is_converted': row.get('is_converted'),
        }

        for key, aliases in field_map.items():
            data[key] = self.get_field_value(row, aliases)

        return data

    def get_field_value(self, row, possible_keys):
        for key in possible_keys:
            if key in row:
                return row[key]
        return None