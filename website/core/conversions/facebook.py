import re
from website import settings
from .base import ConversionService

class FacebookConversionService(ConversionService):
    def _construct_payload(self, data: dict) -> dict:
        instant_form_lead_id = data.get('instant_form_lead_id')

        if instant_form_lead_id:
            return self._build_conversion_leads_payload(data)
        else:
            return self._build_website_leads_payload(data)

    def _build_conversion_leads_payload(self, data: dict) -> dict:
        event_name = data.get('event_name')

        custom_data = {
            'lead_event_source': settings.COMPANY_NAME,
            'event_source': 'crm',
        }

        if event_name == 'event_booked':
            if data.get('event_id'):
                custom_data.update({
                    'currency': settings.DEFAULT_CURRENCY,
                    'value': data.get('value'),
                    'order_id': data.get('event_id'),
                })

        return {
            'data': [
                {
                    'event_name': event_name,
                    'event_time': data.get('event_time'),
                    'action_source': 'system_generated',
                    'user_data': {
                        'lead_id': data.get('instant_form_lead_id'),
                        'ph': [self.hash_to_sha256(data.get('phone_number'))],
                    },
                    'custom_data': custom_data,
                }
            ]
        }

    def _build_website_leads_payload(self, data: dict) -> dict:
        event_name = data.get('event_name')
        user_data = {
            'ph': [
                self.hash_to_sha256(data.get('phone_number'))
            ],
            'client_ip_address': data.get('ip_address'),
            'client_user_agent': data.get('user_agent'),
            'fbc': data.get('click_id'),
            'fbp': data.get('client_id'),
        }

        event = {
            'event_name': event_name,
            'event_time': data.get('event_time'),
            'action_source': 'website',
            'user_data': user_data,
        }

        if event_name == 'event_booked':
            if data.get('event_id'):
                event.update({
                    'custom_data': {
                        'currency': settings.DEFAULT_CURRENCY,
                        'value': data.get('value'),
                        'order_id': data.get('event_id'),
                    }
                })

        self._add_valid_property(event, 'event_source_url', data.get('landing_page'))

        return {
            'data': [event]
        }
    
    def _add_valid_property(self, target: dict, key: str, value):
        if value:
            target[key] = value

    def _get_endpoint(self) -> str:
        pixel_id = self.options.get('pixel_id')
        access_token = self.options.get('access_token')
        version = self.options.get('version')
        return f'https://graph.facebook.com/{version}/{pixel_id}/events?access_token={access_token}'

    def _get_service_name(self) -> str:
        return 'facebook'
    
    def _is_valid(self, data: dict) -> bool:
        lead_id = data.get('instant_form_lead_id')
        if lead_id:
            return True

        client_id = data.get('client_id')
        if client_id and self._is_valid_client_id(client_id):
            return True

        return False
    
    def _is_valid_client_id(self, fbp_cookie: str) -> bool:
        fbp_pattern = re.compile(r'^fb\.\d+\.\d+\.\d+$')
        
        return bool(fbp_pattern.match(fbp_cookie))