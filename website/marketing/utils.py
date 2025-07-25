from django.http import HttpRequest
from urllib.parse import parse_qs, urlparse
from dateutil import parser

from core.utils import normalize_phone_number
from .enums import ConversionServiceType, MarketingParams
from core.models import Ad, AdCampaign, AdGroup

CLICK_ID_KEYS = ["gclid", "gbraid", "wbraid", "msclkid", "fbclid", "li_fat_id"]

class MarketingHelper:
    def __init__(self, request: HttpRequest):
        self.request = request
        
        self.landing_page = (
            self.request.headers.get('Referer')
            if self.request.method == 'POST'
            else self.request.build_absolute_uri()
        )
        parsed_url = urlparse(self.landing_page)
        self.params = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}

        self.external_id = self.request.session.get('external_id')
        self.ip = self.get_client_ip()
        self.user_agent = self.request.META.get('HTTP_USER_AGENT')

        self.keyword = self.params.get('keyword')
        self.source = self.params.get('source')
        self.medium = self.params.get('medium', self.get_medium())
        self.channel = self.params.get('channel')

        marketing_params = self._get_marketing_params()

        self.click_id = marketing_params.get('click_id')
        self.platform_id = marketing_params.get('platform_id')
        self.client_id = marketing_params.get('client_id')

        self.ad = self.get_or_create_ad()

    def to_dict(self):
        exclude = {'request', 'ad'}
        data = {
            key: value
            for key, value in self.__dict__.items()
            if key not in exclude
        }

        if self.ad:
            data['ad_id'] = self.ad.ad_id
            data['ad_name'] = self.ad.name
            data['ad_group_id'] = self.ad.ad_group.ad_group_id
            data['ad_group_name'] = self.ad.ad_group.name
            data['ad_campaign_id'] = self.ad.ad_group.ad_campaign.ad_campaign_id
            data['ad_campaign_name'] = self.ad.ad_group.ad_campaign.name

        return data

    def get_cookie(self, cookie_name):
        """
        Returns the value of a cookie if it exists, otherwise None.
        """
        return self.request.COOKIES.get(cookie_name)

    def get_medium(self):
        if self.is_paid():
            return "paid"
        else:
            return "organic"

    def is_paid(self):
        """
        Determines if the traffic is from a paid source (based on query params).
        """
        return any(self.params.get(key) for key in CLICK_ID_KEYS)

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

    def _get_marketing_params(self) -> dict:
        """
        Utility function to extract marketing parameters from the URL and cookies.
        Extracts click_id from the URL, client_id from cookies, and platform_id based on the URL parameters.
        """
        # Step 1: Extract `click_id` and `platform_id` from the URL
        click_id = None
        platform_id = None
        client_id = None

        for key in MarketingParams.GoogleURLClickIDKeys.value:
            click_id = self.params.get(key)
            if click_id:
                platform_id = ConversionServiceType.GOOGLE.value
                break

        if not click_id:
            fbclid = self.params.get(MarketingParams.FacebookURLClickID.value)
            if fbclid:
                click_id = fbclid
                platform_id = ConversionServiceType.FACEBOOK.value

        # Step 2: Extract `client_id` from cookies based on `platform_id`
        if platform_id == ConversionServiceType.GOOGLE:
            client_id = self.request.COOKIES.get(MarketingParams.GoogleAnalyticsCookieClientID.value)
        elif platform_id == ConversionServiceType.FACEBOOK:
            client_id = self.request.COOKIES.get(MarketingParams.FacebookCookieClientID.value)

        # Step 3: Return the extracted values
        return {
            "click_id": click_id,
            "client_id": client_id,
            "platform_id": platform_id
        }

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
        'platform': ['platform'],
        'form_id': ['form_id'],
        'is_organic': ['is_organic'],
        'campaign_id': ['campaign_id'],
        'campaign_name': ['campaign_name'],
        'adset_id': ['adset_id'],
        'adset_name': ['adset_name'],
        'ad_id': ['ad_id'],
        'ad_name': ['ad_name'],
        'email': ['email'],
        'city': ['city', 'ciudad'],
        'created_time': ['created_time'],
    }

    data = {}

    for key in FIELD_MAP:
        if key in form_values:
            data[key] = form_values[key]

    for key, possible_names in FIELD_MAP.items():
        if key not in data:
            value = get_field_value(form_values, possible_names)
            if value:
                if key == 'phone_number':
                    data[key] = normalize_phone_number(value)
                if key == 'created_time':
                    data[key] = parse_datetime(value) if should_parse_datetime else value
                else:
                    data[key] = value
    
    return data


def get_field_value(form_values, possible_names):
    field_data = form_values.get('field_data', [])
    if not isinstance(field_data, list):
        return None

    for name in possible_names:
        for field in field_data:
            if name.lower() in field.get('name', '').lower():
                return field.get('values', [None])[0]

    return None

def parse_datetime(value):
        if not value:
            return None
        try:
            return parser.isoparse(value)
        except (ValueError, TypeError):
            return None