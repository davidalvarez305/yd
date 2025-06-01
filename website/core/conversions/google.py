import re

from marketing.enums import ConversionServiceType
from website import settings
from .base import ConversionService

class GoogleAnalyticsConversionService(ConversionService):
    def _construct_payload(self, data: dict) -> dict:
        return {
            'client_id': data.get('client_id'),
            'events': [
                {
                    'name': data.get('event_name'),
                    'params': {
                        'value': data.get('value', settings.DEFAULT_LEAD_VALUE),
                        'currency': data.get('currency', settings.DEFAULT_CURRENCY),
                    },
                }
            ],
            'user_data': {
                'email': [self.hash_to_sha256(data.get('email'))],
                'phone': [self.hash_to_sha256(data.get('phone_number'))],
            }
        }

    def _get_endpoint(self) -> str:
        return (
            'https://www.google-analytics.com/mp/collect'
            f"?measurement_id={self.options.get('google_analytics_id')}"
            f"&api_secret={self.options.get('google_analytics_api_key')}"
        )

    def _get_service_name(self) -> str:
        return 'google_analytics_4'
    
    def _is_valid(self, data: dict) -> bool:
        client_id = data.get('client_id')
        if not client_id or not self._is_valid_client_id(client_id):
            return False

        return True

    def _is_valid_client_id(self, client_id: str) -> bool:
        client_id_pattern = re.compile(r'^GA1\.1\.\d+\.\d+$')
        
        return bool(client_id_pattern.match(client_id))