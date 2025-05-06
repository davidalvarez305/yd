from .base import ConversionService
from django.conf import settings

class GoogleConversionService(ConversionService):
    def construct_payload(self) -> dict:
        return {
            "client_id": self.conversion_data["client_id"],
            "events": [{
                "name": self.conversion_data["event_name"],
                "params": {
                    "value": self.conversion_data.get("value", 100.0),
                    "currency": "USD",
                },
            }],
            "user_data": {
                "email": [self.hash_to_sha256(self.conversion_data.get("email"))],
                "phone": [self.hash_to_sha256(self.conversion_data.get("phone_number"))],
            }
        }

    def get_endpoint(self) -> str:
        return (
            f"https://www.google-analytics.com/mp/collect"
            f"?measurement_id={settings.GOOGLE_ANALYTICS_ID}"
            f"&api_secret={settings.GOOGLE_ANALYTICS_API_KEY}"
        )