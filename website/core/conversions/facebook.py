from .base import ConversionService

class FacebookConversionService(ConversionService):
    def _construct_payload(self, data: dict) -> dict:
        user_data = {
            "em": [self.hash_to_sha256(data.get("email"))],
            "ph": [self.hash_to_sha256(data.get("phone_number"))],
            "client_ip_address": data.get("ip_address"),
            "client_user_agent": data.get("user_agent"),
        }

        event = {
            "event_name": data.get("event_name"),
            "event_time": data.get("event_time"),
            "user_data": user_data,
            "action_source": data.get("action_source", "website"),
        }

        return {
            "data": [event]
        }

    def _get_endpoint(self) -> str:
        pixel_id = self.options.get("pixel_id")
        access_token = self.options.get("access_token")
        return f"https://graph.facebook.com/20.0/{pixel_id}/events?access_token={access_token}"

    def _get_service_name(self) -> str:
        return "facebook"