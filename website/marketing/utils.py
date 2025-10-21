import json
import random
import re
from django.http import HttpRequest
from urllib.parse import parse_qs, urlparse, parse_qsl
from dateutil import parser

from core.utils import normalize_phone_number
from .enums import ConversionServiceType, MarketingParams
from core.models import Ad, AdCampaign, AdGroup, LeadMarketing, LeadMarketingMetadata, TrackingPhoneCall

CLICK_ID_KEYS = ["gclid", "gbraid", "wbraid", "msclkid", "fbclid", "li_fat_id"]

class MarketingHelper:
    def __init__(self, request: HttpRequest):
        self.request = request
        
        self.landing_page = (
            self.request.headers.get('Referer')
            if self.request.method == 'POST'
            else self.request.build_absolute_uri()
        )
        
        self.params = generate_params_dict_from_url(self.landing_page)
        self.external_id = self.request.session.get('external_id')
        self.ip = self.get_client_ip()
        self.user_agent = self.request.META.get('HTTP_USER_AGENT')
        self.platform_id = self.get_platform_id()
        self.ad = self.get_or_create_ad()
        self.metadata = self.create_metadata()
        self.lead_marketing = self.create_marketing_data()
    
    def add_metadata_from_list(self, data = []):
        metadata = {}
        for entry in data:
            metadata[entry.get('key')] = entry.get('value')

        self.metadata = metadata

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
        return create_ad_from_params(params=self.params, cookies=self.request.COOKIES)

    def get_platform_id(self):
        return get_platform_id_from_params(params=self.params, cookies=self.request.COOKIES)

def is_paid_traffic(request: HttpRequest) -> bool:
    landing_page = request.build_absolute_uri()

    for key in CLICK_ID_KEYS:
        if key in landing_page:
            return True
        
    paid_cookies = [
        MarketingParams.FacebookCookieClickID.value,
        MarketingParams.GoogleSearchCookieClickID.value,
    ]

    for cookie in paid_cookies:
        if request.COOKIES.get(cookie):
            return True

    return False

def parse_datetime(value):
        if not value:
            return None
        try:
            return parser.isoparse(value)
        except (ValueError, TypeError):
            return None

def generate_random_big_int_id() -> int:
    return random.randint(1, (2**63) - 1)

def random_selection(length: int) -> int:
    return random.randint(0, length)

def generate_params_dict_from_url(url: str):
    return dict(parse_qsl(urlparse(url).query))

def is_valid_int(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False

def create_ad_from_params(params: dict, cookies: dict):
    ad_id = params.get('ad_id')
    ad_name = params.get('ad_name')

    ad_group_id = params.get('ad_group_id')
    ad_group_name = params.get('ad_group_name')

    ad_campaign_id = params.get('ad_campaign_id')
    ad_campaign_name = params.get('ad_campaign_name')

    keyword = params.get('keyword')

    platform_id = get_platform_id_from_params(params=params, cookies=cookies)

    if not all([is_valid_int(ad_id), is_valid_int(ad_group_id), is_valid_int(ad_campaign_id), platform_id]):
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

    if keyword:
        ad = Ad.objects.filter(name=keyword).first()
        if ad:
            return ad

        ad_id = generate_random_big_int_id()
        ad_name = keyword

    ad, _ = Ad.objects.get_or_create(
        ad_id=ad_id,
        defaults={
            'platform_id': platform_id,
            'name': ad_name,
            'ad_group': ad_group,
        }
    )
    
    return ad

def get_platform_id_from_params(params: dict, cookies: dict):
    for key in MarketingParams.GoogleURLClickIDKeys.value:
        click_id = params.get(key)
        if click_id:
            return ConversionServiceType.GOOGLE.value
    
    gcl_aw = cookies.get(MarketingParams.GoogleSearchCookieClickID.value)
    if gcl_aw:
        return ConversionServiceType.GOOGLE.value

    fbclid = params.get(MarketingParams.FacebookURLClickID.value)
    if fbclid:
        return ConversionServiceType.FACEBOOK.value
    
    fbc = cookies.get(MarketingParams.FacebookCookieClickID.value)
    if fbc:
        return ConversionServiceType.FACEBOOK.value

    return None

def parse_google_ads_cookie(value: str):
    match = re.search(r'GCL\.[^\.]+\.(.*?)$', value)
    
    if match:
        return match.group(1)
    else:
        return None

def is_google_ads_call_asset(phone_call: TrackingPhoneCall) -> bool:
    source_name = phone_call.metadata.filter(key='source_name').first()

    if source_name:
        return source_name.value == 'YD Cocktails Google Ads Call Assets'

    return False