from django.conf import settings
from .base import ConversionService

class FacebookConversionService(ConversionService):
    def construct_payload(self) -> dict:
        user_data = {
            "em": [self.hash_to_sha256(self.conversion_data.get("email"))],
            "ph": [self.hash_to_sha256(self.conversion_data.get("phone_number"))],
            "client_ip_address": self.conversion_data.get("ip_address"),
            "client_user_agent": self.conversion_data.get("user_agent"),
        }

        event = {
            "event_name": self.conversion_data["event_name"],
            "event_time": self.conversion_data.get("event_time"),
            "user_data": user_data,
            "action_source": self.conversion_data.get("action_source", "website"),
        }

        return {
            "data": [event]
        }

    def get_endpoint(self) -> str:
        pixel_id = settings.FACEBOOK_PIXEL_ID
        access_token = settings.FACEBOOK_ACCESS_TOKEN
        return f"https://graph.facebook.com/v17.0/{pixel_id}/events?access_token={access_token}"