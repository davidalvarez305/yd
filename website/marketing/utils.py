import json
from django.http import HttpRequest
from urllib.parse import parse_qs, urlparse
from dateutil import parser

from core.utils import normalize_phone_number
from .enums import ConversionServiceType, MarketingParams
from core.models import Ad, AdCampaign, AdGroup, LeadMarketing, LeadMarketingMetadata

CLICK_ID_KEYS = ["gclid", "gbraid", "wbraid", "msclkid", "fbclid", "li_fat_id"]

class MarketingHelper:
    def __init__(self, request: HttpRequest):
        self.request = request
        
        self.landing_page = (
            self.request.headers.get('Referer')
            if self.request.method == 'POST'
            else self.request.build_absolute_uri()
        )
        
        self.params = self.request_params()
        self.external_id = self.request.session.get('external_id')
        self.ip = self.get_client_ip()
        self.user_agent = self.request.META.get('HTTP_USER_AGENT')
        self.platform_id = self.get_platform_id()
        self.ad = self.get_or_create_ad()
        self.metadata = self.create_metadata()
        self.lead_marketing = self.create_marketing_data()
    
    def request_params(self):
        parsed_url = urlparse(self.landing_page)
        params = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}
        return params
    
    def create_marketing_data(self):
        return {
            'ip': self.ip,
            'external_id': self.external_id,
            'user_agent': self.user_agent,
            'metadata': json.dumps(self.metadata),
        }

    def create_metadata(self):
        metadata = {}

        for key, value in self.request.COOKIES.items():
            metadata[key] = value

        for key, value in self.params.items():
            metadata[key] = value

        return metadata

    def save_metadata(self, lead_marketing: LeadMarketing):
        for key, value in self.metadata.items():
            entry = LeadMarketingMetadata(
                key=key,
                value=value,
                lead_marketing=lead_marketing,
            )
            entry.save()

    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return self.request.META.get('REMOTE_ADDR')

    def get_or_create_ad(self):
        """
        Fetches or creates an ad based on URL parameters.
        """
        ad_id = self.params.get('ad_id')
        ad_name = self.params.get('ad_name')

        ad_group_id = self.params.get('ad_group_id')
        ad_group_name = self.params.get('ad_group_name')

        ad_campaign_id = self.params.get('ad_campaign_id')
        ad_campaign_name = self.params.get('ad_campaign_name')

        if not all([ad_id, ad_group_id, ad_campaign_id, self.platform_id]):
            return None

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

        ad, _ = Ad.objects.get_or_create(
            ad_id=ad_id,
            defaults={
                'platform_id': self.platform_id,
                'name': ad_name,
                'ad_group': ad_group,
            }
        )
        
        return ad

    def get_platform_id(self) -> dict:
        for key in MarketingParams.GoogleURLClickIDKeys.value:
            click_id = self.params.get(key)
            if click_id:
                return ConversionServiceType.GOOGLE.value
        
        fbclid = self.params.get(MarketingParams.FacebookURLClickID.value)
        if fbclid:
            return ConversionServiceType.FACEBOOK.value

        return None

def is_paid_traffic(request: HttpRequest) -> bool:
    landing_page = request.build_absolute_uri()

    for key in CLICK_ID_KEYS:
        if key in landing_page:
            return True

    return False

def get_facebook_form_values(form_values, should_parse_datetime):
    FIELD_MAP = {
        'full_name': ['full_name', 'nombre_completo', 'name'],
        'message': ['message', 'services', 'city', 'brief_description', 'ciudad'],
        'phone_number': ['phone_number', 'telefono'],
        'email': ['email'],
        'city': ['city', 'ciudad'],
        'platform': ['platform'],
        'form_id': ['form_id'],
        'is_organic': ['is_organic'],
        'campaign_id': ['campaign_id'],
        'campaign_name': ['campaign_name'],
        'adset_id': ['adset_id'],
        'adset_name': ['adset_name'],
        'ad_id': ['ad_id'],
        'ad_name': ['ad_name'],
        'created_time': ['created_time'],
    }

    data = {}

    field_data = form_values.get('field_data', [])
    if not isinstance(field_data, list):
        raise TypeError('Field data is not a list.')

    for key in FIELD_MAP:
        if key in form_values:
            data[key] = form_values[key]

    for key, possible_names in FIELD_MAP.items():
        if key not in data:
            value = get_field_value(field_data, possible_names)
            if value:
                if key == 'phone_number':
                    data[key] = normalize_phone_number(value)
                elif key == 'created_time' and should_parse_datetime:
                    data[key] = parse_datetime(value)
                else:
                    data[key] = value

    return data


def get_field_value(field_data, possible_names):
    for field in field_data:
        field_name = field.get('name', '')
        if any(name in field_name for name in possible_names):
            values = field.get('values')
            if values:
                return values[0]
    return None

def parse_datetime(value):
        if not value:
            return None
        try:
            return parser.isoparse(value)
        except (ValueError, TypeError):
            return None