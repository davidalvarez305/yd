from .base import ConversionService

class GoogleConversionService(ConversionService):
    def _construct_payload(self, data: dict) -> dict:
        return {
            "client_id": data.get("client_id"),
            "events": [{
                "name": data.get("event_name"),
                "params": {
                    "value": data.get("value", 100.0),
                    "currency": "USD",
                },
            }],
            "user_data": {
                "email": [self.hash_to_sha256(data.get("email"))],
                "phone": [self.hash_to_sha256(data.get("phone_number"))],
            }
        }

    def _get_endpoint(self) -> str:
        return (
            "https://www.google-analytics.com/mp/collect"
            f"?measurement_id={self.options.get('google_analytics_id')}"
            f"&api_secret={self.options.get('google_analytics_api_key')}"
        )

    def _get_service_name(self) -> str:
        return "google_analytics_4"