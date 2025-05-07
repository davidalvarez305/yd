from .base import ConversionService
from django.conf import settings

class GoogleConversionService(ConversionService):
    def _construct_payload(self) -> dict:
        return {
            "client_id": self.data.get('client_id'),
            "events": [{
                "name": self.data.get('event_name'),
                "params": {
                    "value": self.data.get("value", 100.0),
                    "currency": "USD",
                },
            }],
            "user_data": {
                "email": [self.hash_to_sha256(self.data.get("email"))],
                "phone": [self.hash_to_sha256(self.data.get("phone_number"))],
            }
        }

    def _get_endpoint(self) -> str:
        return (
            "https://www.google-analytics.com/mp/collect"
            f"?measurement_id={settings.GOOGLE_ANALYTICS_ID}"
            f"&api_secret={settings.GOOGLE_ANALYTICS_API_KEY}"
        )

    def _get_service_name(self) -> str:
        return "google_analytics_4"