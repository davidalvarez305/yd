import json
from dateutil import parser
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Ad, AdCampaign, AdGroup, Lead, LeadMarketing
from marketing.enums import ConversionServiceType, MarketingParams
from core.utils import extract_url_param_value, generate_random_long_int, normalize_phone_number

class Command(BaseCommand):
    help = 'Import enriched leads from a JSON file and either save to DB or export to data.json.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to JSON file with enriched lead data'
        )
        parser.add_argument(
            '--save',
            action='store_true',
            help='Save leads to the database'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Export parsed leads to data.json'
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])

        if not file_path.exists():
            self.stderr.write(self.style.ERROR(f"❌ File not found: {file_path}"))
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                leads = json.load(f)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Failed to load JSON: {e}"))
            return

        if not isinstance(leads, list):
            self.stderr.write(self.style.ERROR("❌ Expected a list of lead objects in the JSON file."))
            return

        entries = []
        for lead in leads:
            try:
                if 'test' in lead.get('full_name') or lead.get('full_name') in {'David Alvarez', 'Yovana Lacalle', ''}:
                    continue

                is_valid = normalize_phone_number(lead.get('phone_number'))
                if not is_valid:
                    continue

                exists = Lead.objects.filter(phone_number=normalize_phone_number(lead.get('phone_number'))).exists()
                if exists:
                    continue

                entries.append(self.extract_entry(lead, options['save']))
            except Exception as e:
                continue

        if options['json']:
            with open('align_leads.json', 'w', encoding='utf-8') as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
            self.stdout.write(self.style.SUCCESS(f"✅ Exported {len(entries)} leads to align_leads.json"))

        if options['save']:
            count = 0
            for entry in entries:
                try:
                    with transaction.atomic():
                        lead = Lead.objects.create(
                            phone_number=entry.get('phone_number'),
                            full_name=entry.get('full_name'),
                            message=entry.get('message'),
                            created_at=entry.get('created_at'),
                            opt_in_text_messaging=entry.get('opt_in_text_messaging'),
                        )

                        client_id = None
                        platform_id = None
                        ad = None

                        landing_page = entry.get('landing_page') or ''

                        if MarketingParams.FacebookURLClickID.value in landing_page:
                            client_id = entry.get('facebook_client_id')
                            platform_id = ConversionServiceType.FACEBOOK.value
                        else:
                            for key in MarketingParams.GoogleURLClickIDKeys.value:
                                if key in landing_page:
                                    client_id = entry.get('google_client_id')
                                    platform_id = ConversionServiceType.GOOGLE.value
                                    break
                        
                        if entry.get('ad_campaign'):
                            ad_campaign_name = entry.get('ad_campaign')
                            ad_campaign_id = entry.get('campaign_id')
                            ad_group_id = entry.get('ad_set_id') if entry.get('ad_set_id') else entry.get('ad_group_id')
                            ad_group_name = entry.get('ad_set_name') if entry.get('ad_set_name') else entry.get('ad_group_name')

                            ad_campaign, _ = AdCampaign.objects.get_or_create(
                                ad_campaign_id=ad_campaign_id,
                                defaults={
                                    'name': ad_campaign_name,
                                }
                            )

                            ad_group, _ = AdGroup.objects.get_or_create(
                                ad_group_id=ad_group_id,
                                defaults={
                                    'name': ad_group_name,
                                    'ad_campaign': ad_campaign,
                                }
                            )

                            keyword = entry.get('keyword')

                            # Handle Google Ads
                            if keyword:
                                google_ad = Ad.objects.filter(name=keyword).first()

                                if not google_ad:
                                    ad.id = generate_random_long_int()
                                    ad.name = keyword
                                    ad.ad_group = ad_group
                                    ad.platform_id = platform_id
                                    ad.save()

                                    ad = ad
                                else:
                                    ad = google_ad
                            
                            # Handle Facebook Ads
                            creative = extract_url_param_value(entry.get('landing_page'), 'creative')
                            if creative:
                                facebook_ad = Ad.objects.filter(name=creative).first()
                                if facebook_ad is None:
                                    ad.id = generate_random_long_int()
                                    ad.name = creative
                                    ad.ad_group = ad_group
                                    ad.platform_id = platform_id
                                    ad.save()
                                else:
                                    ad = facebook_ad

                            marketing = LeadMarketing(
                                lead=lead,
                                source=entry.get('source'),
                                medium=entry.get('medium'),
                                channel=entry.get('channel'),
                                landing_page=entry.get('landing_page'),
                                click_id=entry.get('click_id'),
                                client_id=client_id,
                                instant_form_id=entry.get('instant_form_id'),
                                instant_form_lead_id=entry.get('instant_form_lead_id'),
                            )

                            if ad:
                                marketing.ad = ad

                            marketing.save()
                        count += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"❌ Failed to process lead {entry.get('phone_number')}: {e}"))

            self.stdout.write(self.style.SUCCESS(f"✅ Successfully saved {count} new leads to the database"))

    def extract_entry(self, lead, parse_datetime=False):
        return {
            'full_name': lead.get('full_name'),
            'phone_number': normalize_phone_number(lead.get('phone_number')),
            'message': lead.get('message'),
            'created_at': self.parse_datetime(lead.get('created_at')) if parse_datetime else lead.get('created_at'),
            'opt_in_text_messaging': lead.get('opt_in_text_messaging'),

            # Marketing fields
            'source': lead.get('source'),
            'medium': lead.get('medium'),
            'channel': lead.get('channel'),
            'landing_page': lead.get('landing_page'),
            'referrer': lead.get('referrer'),
            'click_id': lead.get('click_id'),
            'facebook_click_id': lead.get('facebook_click_id'),
            'facebook_client_id': lead.get('facebook_client_id'),
            'google_client_id': lead.get('google_client_id'),
            'external_id': lead.get('external_id'),
            'instant_form_id': lead.get('instant_form_id'),
            'instant_form_lead_id': lead.get('instant_form_lead_id'),
            'instant_form_name': lead.get('instant_form_name'),
        }

    def parse_datetime(self, value):
        if not value:
            return None
        try:
            return parser.isoparse(value)
        except (ValueError, TypeError):
            self.stderr.write(self.style.WARNING(f"⚠️ Invalid datetime format: {value}"))
            return None