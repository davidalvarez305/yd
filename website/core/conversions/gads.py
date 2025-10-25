import datetime
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from website import settings
from core.utils import load_google_credentials
from .base import ConversionService
from core.logger import logger

class GoogleAdsConversionService(ConversionService):
    def __init__(self, options: dict):
        super().__init__(options)
        self.credentials = load_google_credentials()
        opts = {
            "developer_token": self.options.get('developer_token'),
            "client_id": self.credentials.client_id,
            "client_secret": self.credentials.client_secret,
            "refresh_token": self.credentials.refresh_token,
            "login_customer_id": self.options.get('customer_id'),
        }
        self.client = GoogleAdsClient.load_from_dict(opts)
        self.google_ads_customer_id = self.options.get('customer_id')
        self.conversion_actions = self.options.get('conversion_actions')

    def _get_service_name(self) -> str:
        return "google_ads"

    def _is_valid(self, data: dict) -> bool:
        return bool(data.get('gclid'))

    def _construct_payload(self, data: dict) -> dict:
        timestamp = data.get('event_time')
        event_time = datetime.fromtimestamp(timestamp, tz=datetime.timezone.get_current_timezone())

        payload = {
                "customer_id": self.google_ads_customer_id,
                "conversion_action_id": self.conversion_actions.get(data.get('event_name')),
                "gclid": data.get("gclid"),
                "conversion_date_time": event_time.strftime("%Y-%m-%d %H:%M:%S%z"),
                "conversion_value": data.get('value'),
            }
        
        if data.get('event_id'):
            payload.update({
                'order_id': data.get('event_id')
            })

        return payload

    def send_conversion(self, data: dict):
        if not self._is_valid(data):
            return

        payload = self._construct_payload(data)

        try:
            conversion_upload_service = self.client.get_service("ConversionUploadService")
            conversion_action_service = self.client.get_service("ConversionActionService")
            click_conversion = self.client.get_type("ClickConversion")

            click_conversion.conversion_action = conversion_action_service.conversion_action_path(
                payload.get('customer_id'), payload.get('conversion_action_id')
            )

            click_conversion.gclid = payload.get('gclid')

            click_conversion.conversion_value = float(payload.get('conversion_value'))
            click_conversion.conversion_date_time = payload.get('conversion_date_time')
            click_conversion.currency_code = getattr(settings, "DEFAULT_CURRENCY", "USD")

            if payload.get("order_id"):
                click_conversion.order_id = payload.get('order_id')

            request = self.client.get_type('UploadClickConversionsRequest')
            request.customer_id = payload.get('customer_id')
            request.conversions.append(click_conversion)
            request.partial_failure = True

            conversion_upload_service.upload_click_conversions(request=request)

        except Exception as e:
            logger.exception(f"Error during Google Ads Conv Reporting: {e}", exc_info=True)
            return None