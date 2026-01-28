import json
from django.http import HttpRequest
from core.utils import generate_params_dict_from_url, get_platform_id_from_params, create_ad_from_params

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

    def save_metadata(self, lead_marketing):
        from core.models import LeadMarketingMetadata
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