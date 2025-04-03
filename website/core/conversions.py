from abc import ABC, abstractmethod
import requests
import json

class ConversionService(ABC):
    @abstractmethod
    def send_form_conversion(self, payload):
        """Send form conversion data"""
        pass
    
    @abstractmethod
    def send_phone_conversion(self, payload):
        """Send phone conversion data"""
        pass

class GoogleConversionService(ConversionService):
    def __init__(self, measurement_id, api_secret_key):
        self.measurement_id = measurement_id
        self.api_secret_key = api_secret_key
        self.endpoint = "https://www.google-analytics.com/mp/collect"
    
    def send_form_conversion(self, payload):
        try:
            json_data = json.dumps(payload)

            url = f"{self.endpoint}?measurement_id={self.measurement_id}&api_secret={self.api_secret_key}"

            response = requests.post(url, data=json_data, headers={"Content-Type": "application/json"})

            if response.status_code not in [200, 204]:
                return f"Google API returned non-200 status code: {response.status_code}"
        except requests.exceptions.RequestException as err:
            return

    def send_phone_conversion(self, payload):
        pass
    
class FacebookConversionService(ConversionService):
    def __init__(self, pixel_id, access_token):
        self.pixel_id = pixel_id
        self.access_token = access_token
        self.endpoint = f"https://graph.facebook.com/v12.0/{self.pixel_id}/events"
    
    def send_form_conversion(self, payload):
        try:
            data = {
                "data": [
                    {
                        "event_name": "Lead",
                        "event_time": int(payload['event_time']),
                        "user_data": {
                            "em": payload.get("email", ""),
                            "ph": payload.get("phone", ""),
                            "client_ip_address": payload.get("ip", ""),
                            "client_user_agent": payload.get("user_agent", "")
                        },
                        "custom_data": {
                            "value": payload.get("value", 0),
                            "currency": "USD"
                        }
                    }
                ]
            }

            params = {
                'access_token': self.access_token
            }
            response = requests.post(self.endpoint, params=params, json=data)

            if response.status_code != 200:
                return f"Facebook API returned non-200 status code: {response.status_code}"
            
        except requests.exceptions.RequestException as err:
            return

    def send_phone_conversion(self, payload):
        pass