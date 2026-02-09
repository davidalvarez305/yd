import json
from urllib.parse import parse_qsl, urlparse
from django.http import HttpRequest

from core.utils import create_ad_from_params, generate_random_big_int_id, is_valid_int

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
        self.metadata = self._create_metadata()
        self.ad = create_ad_from_params(params=self.metadata)
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
    
    def _is_paid_traffic(self) -> bool:
        from core.models import AdPlatformParam
        params = AdPlatformParam.objects.all()

        for each in params:
            if each.param in self.metadata:
                return True

        return False