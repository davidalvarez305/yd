import re
from marketing.enums import ConversionServiceType
from website import settings
from .base import ConversionService

class FacebookConversionService(ConversionService):
    def _construct_payload(self, data: dict) -> dict:
        user_data = {
            'em': [self.hash_to_sha256(data.get('email'))],
            'ph': [self.hash_to_sha256(data.get('phone_number'))],
            'client_ip_address': data.get('ip_address'),
            'client_user_agent': data.get('user_agent'),
            'fbc': data.get('click_id')
        }

        web_payload = {
            'data': [
                {
                    'event_name': data.get('event_name'),
                    'event_time': data.get('event_time'),
                    'action_source': 'website',
                    'user_data': user_data,
                }
            ]
        }

        click_id = data.get('click_id')

        if click_id:
            return web_payload
        
        lead_ads_payload = {
            'data': [
                {
                    'event_name': data.get('event_name'),
                    'event_time': data.get('event_time'),
                    'action_source': 'crm',
                    'user_data': {
                        'lead_id': data.get('lead_id_id')
                    },
                    'custom_data': {
                        'lead_event_source': settings.COMPANY_NAME,
                        'event_source': 'crm'
                    }
                }
            ]
        }

        return lead_ads_payload

    def _get_endpoint(self) -> str:
        pixel_id = self.options.get('pixel_id')
        access_token = self.options.get('access_token')
        return f'https://graph.facebook.com/22.0/{pixel_id}/events?access_token={access_token}'

    def _get_service_name(self) -> str:
        return 'facebook'
    
    def _is_valid(self, data: dict) -> bool:
        if getattr(self, 'platform_id', '') != ConversionServiceType.FACEBOOK.value:
            return False
        
        click_id = data.get('click_id')
        if not click_id:
            return data.get('lead_id') is not None

        client_id = data.get('client_id')
        if not client_id or not self._is_valid_client_id(client_id):
            return False
        
        client_id_parts = client_id.split('.')
        if len(client_id_parts) != 4:
            return False
        
        cookie_click_id = client_id_parts[3]
        click_id = data.get('click_id')

        if cookie_click_id != click_id:
            return False

        return True

    def _is_valid_client_id(self, client_id: str) -> bool:
        client_id_pattern = re.compile(r'^fb\.1\.\d+\.[A-Za-z0-9]+$')
        
        return bool(client_id_pattern.match(client_id))