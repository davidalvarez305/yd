import json
from urllib.parse import parse_qsl, urlparse
from django.http import HttpRequest

from core.utils import generate_random_big_int_id, is_valid_int

class MarketingHelper:
    def __init__(self, request: HttpRequest):
        self.request = request
        
        self.landing_page = (
            self.request.headers.get('Referer')
            if self.request.method == 'POST'
            else self.request.build_absolute_uri()
        )
        
        self.params = self._generate_params_dict_from_url()
        self.cookies = self.request.COOKIES
        self.external_id = self.request.session.get('external_id')
        self.ip = self._get_client_ip()
        self.user_agent = self.request.META.get('HTTP_USER_AGENT')
        self.ad = self._create_ad_from_params()
        self.metadata = self._create_metadata()
        self.lead_marketing = self._create_marketing_data()
    
    def add_metadata_from_list(self, data = []):
        metadata = {}
        for entry in data:
            metadata[entry.get('key')] = entry.get('value')

        self.metadata = metadata

    def _create_marketing_data(self):
        return {
            'ip': self.ip,
            'external_id': self.external_id,
            'user_agent': self.user_agent,
            'metadata': json.dumps(self.metadata),
        }

    def _create_metadata(self):
        metadata = {}

        for key, value in self.request.COOKIES.items():
            metadata[key] = value

        for key, value in self.params.items():
            metadata[key] = value

        return metadata

    def _get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return self.request.META.get('REMOTE_ADDR')

    def _generate_params_dict_from_url(self):
        return dict(parse_qsl(urlparse(self.landing_page).query))
    
    def _create_ad_from_params(self):
        from core.models import Ad, AdGroup, AdCampaign, AdPlatform

        if keyword:
            ad = Ad.objects.filter(name=self.params.get('keyword')).first()
            if ad:
                return ad

        ad, _ = Ad.objects.filter(pk=self.params.get('ad_id')).first()
        if ad:
            return ad

        ad_platform = AdPlatform.objects.get(pk=self._get_platform_id_from_params())

        ad_id = self.params.get('ad_id')
        ad_name = self.params.get('ad_name')

        ad_group_id = self.params.get('ad_group_id')
        ad_group_name = self.params.get('ad_group_name')

        ad_campaign_id = self.params.get('ad_campaign_id')
        ad_campaign_name = self.params.get('ad_campaign_name')

        keyword = self.params.get('keyword')

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
            ad_id = generate_random_big_int_id()
            ad_name = keyword

        ad, _ = Ad.objects.create(
            ad_id=ad_id,
            ad_platform=ad_platform,
            name=ad_name,
            ad_group=ad_group,
        )
        
        return ad

    def _get_platform_id_from_params(self):
        from core.models import AdPlatformParam
        marketing_params = AdPlatformParam.objects.all()
        for each in marketing_params:
            if each.param in self.params or each.param in self.cookies:
                return each.ad_platform.pk

    def _parse_google_ads_cookie(self, cookie_value: str | None) -> str | None:
        if not cookie_value:
            return None

        try:
            parts = cookie_value.split(".")
            if len(parts) < 3:
                return None

            gclid = parts[-1]

            if not gclid or len(gclid) < 10:
                return None

            return gclid
        except Exception:
            return None
    
    def _is_paid_traffic(self) -> bool:
        from core.models import AdPlatformParam
        params = AdPlatformParam.objects.all()

        for each in params:
            if each.param in self.metadata:
                return True

        return False