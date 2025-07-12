import re

from marketing.enums import ConversionServiceType
from website import settings
from .base import ConversionService

class GoogleAnalyticsConversionService(ConversionService):
    def _construct_payload(self, data: dict) -> dict:
        event_name = data.get('event_name')

        params = {
            'gclid': data.get('click_id'),
            'value': data.get('value', settings.DEFAULT_LEAD_VALUE),
            'currency': settings.DEFAULT_CURRENCY,
        }

        if event_name == 'event_booked':
            if data.get('event_id'):
                params.update({
                    'order_id': data.get('event_id'),
                    'value': data.get('value'),
                })

        return {
            'client_id': data.get('client_id'),
            'user_id': str(data.get('external_id')),
            'user_agent': data.get('user_agent'),
            'events': [
                {
                    'name': event_name,
                    'params': params,
                }
            ],
            'user_data': {
                'sha256_phone_number': [
                    self.hash_to_sha256(data.get('phone_number'))
                ],
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