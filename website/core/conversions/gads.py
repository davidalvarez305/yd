from datetime import datetime
from django.utils import timezone
from website import settings
from core.logger import logger
from .base import ConversionService
from core.google.api import google_api_service

class GoogleAdsConversionService(ConversionService):
    def __init__(self, **options: dict):
        super().__init__(**options)
        self.client = google_api_service.google_ads_client
        self.customer_id = settings.GOOGLE_ADS_CUSTOMER_ID
        self.conversion_actions = options.get("conversion_actions", {})

    def _get_service_name(self) -> str:
        return "google_ads"

    def _is_valid(self, data: dict) -> bool:
        return bool(data.get("gclid")) and bool(self.conversion_actions.get(data.get("event_name")))

    def _construct_payload(self, data: dict) -> dict:
        timestamp = data.get("event_time", datetime.now().timestamp())
        event_time = datetime.fromtimestamp(timestamp, tz=timezone.get_current_timezone())

        payload = {
            "customer_id": self.customer_id,
            "conversion_action_id": self.conversion_actions.get(data.get("event_name")),
            "gclid": data.get("gclid"),
            "conversion_value": data.get("value"),
            "conversion_date_time": event_time.strftime("%Y-%m-%d %H:%M:%S%z")[:-2] + ":" + event_time.strftime("%z")[-2:],
        }

        if data.get("event_id"):
            payload["order_id"] = data.get('event_id')

        return payload

    def send_conversion(self, data: dict):
        if not self._is_valid(data):
            return

        payload = self._construct_payload(data)
        try:
            upload_service = self.client.get_service("ConversionUploadService")
            action_service = self.client.get_service("ConversionActionService")
            click_conversion = self.client.get_type("ClickConversion")

            click_conversion.conversion_action = action_service.conversion_action_path(
                payload["customer_id"], payload["conversion_action_id"]
            )
            click_conversion.gclid = payload["gclid"]
            click_conversion.conversion_value = float(payload["conversion_value"])
            click_conversion.conversion_date_time = payload["conversion_date_time"]
            click_conversion.currency_code = settings.DEFAULT_CURRENCY

            if payload.get("order_id"):
                click_conversion.order_id = str(payload["order_id"])

            request = self.client.get_type("UploadClickConversionsRequest")
            request.customer_id = payload["customer_id"]
            request.conversions.append(click_conversion)
            request.partial_failure = True

            response = upload_service.upload_click_conversions(request=request)
            return response
        except Exception as e:
            logger.exception(f"Error during Google Ads conversion upload: {e}", exc_info=True)
            return None