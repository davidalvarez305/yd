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
        has_click_id = (
            bool(data.get("gclid"))
            or bool(data.get("gbraid"))
            or bool(data.get("wbraid"))
        )
        return  has_click_id and bool(self.conversion_actions.get(data.get("event_name")))

    def _construct_payload(self, data: dict) -> dict:
        timestamp = data.get("event_time", datetime.now().timestamp())
        event_time = datetime.fromtimestamp(timestamp, tz=timezone.get_current_timezone())
        now = datetime.now(tz=timezone.get_current_timezone())

        conversion_date_time = event_time.strftime("%Y-%m-%d %H:%M:%S%z")[:-2] + ":" + event_time.strftime("%z")[-2:]
        adjustment_date_time = now.strftime("%Y-%m-%d %H:%M:%S%z")[:-2] + ":" + now.strftime("%z")[-2:]

        payload = {
            "customer_id": self.customer_id,
            "conversion_action_id": self.conversion_actions.get(data.get("event_name")),
            "gclid": data.get("gclid"),
            "gbraid": data.get("gbraid"),
            "wbraid": data.get("wbraid"),
            "conversion_date_time": conversion_date_time,
            "adjustment_date_time": adjustment_date_time,
        }

        # Only report value for bookings
        if data.get("event_id"):
            payload["order_id"] = data.get('event_id')
            payload["conversion_value"] = data.get("value")

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
            if payload.get("gclid"):
                click_conversion.gclid = payload["gclid"]
            elif payload.get("gbraid"):
                click_conversion.gbraid = payload["gbraid"]
            elif payload.get("wbraid"):
                click_conversion.wbraid = payload["wbraid"]
            click_conversion.conversion_date_time = payload["conversion_date_time"]
            click_conversion.currency_code = settings.DEFAULT_CURRENCY

            if payload.get("order_id"):
                click_conversion.order_id = str(payload["order_id"])
            
            if payload.get("conversion_value"):
                click_conversion.conversion_value = float(payload["conversion_value"])

            request = self.client.get_type("UploadClickConversionsRequest")
            request.customer_id = payload["customer_id"]
            request.conversions.append(click_conversion)
            request.partial_failure = True

            response = upload_service.upload_click_conversions(request=request)
            return response
        except Exception as e:
            logger.exception(f"Error during Google Ads conversion upload: {e}", exc_info=True)
            return None
    
    def retract_conversion(self, data: dict):
        if not self._is_valid(data):
            return None

        try:
            payload = self._construct_payload(data)
        except Exception as e:
            return None

        try:
            conversion_adjustment_type_enum = self.client.enums.ConversionAdjustmentTypeEnum
            conversion_adjustment_type = conversion_adjustment_type_enum.RETRACTION.value

            conversion_adjustment = self.client.get_type("ConversionAdjustment")
            conversion_action_service = self.client.get_service("ConversionActionService")
            
            if "customer_id" not in payload or "conversion_action_id" not in payload:
                return None

            conversion_adjustment.conversion_action = conversion_action_service.conversion_action_path(
                payload["customer_id"], payload["conversion_action_id"]
            )

            conversion_adjustment.adjustment_type = conversion_adjustment_type
            conversion_adjustment.adjustment_date_time = payload["adjustment_date_time"]
            
            if data.get('event_name') == "event_booked" and payload.get("event_id"):
                conversion_adjustment.order_id = str(payload["event_id"])
            elif payload.get("gclid") and payload.get("conversion_date_time"):
                conversion_adjustment.gclid_date_time_pair.gclid = payload["gclid"]
                conversion_adjustment.gclid_date_time_pair.conversion_date_time = (
                    payload["conversion_date_time"]
                )

            service = self.client.get_service("ConversionAdjustmentUploadService")
            request = self.client.get_type("UploadConversionAdjustmentsRequest")
            request.customer_id = payload["customer_id"]
            request.conversion_adjustments.append(conversion_adjustment)
            request.partial_failure = True

            response = service.upload_conversion_adjustments(request=request)

            if response.partial_failure_error:
                for error in response.partial_failure_error.details:
                    logger.error(f"Partial failure occurred: {error}")
            
            for result in response.results:
                logger.debug(f"Retracted conversion with order ID: {result.order_id} for conversion action: {result.conversion_action}")

            return response

        except Exception as e:
            logger.error(f"Error retracting conversion: {e}", exc_info=True)
            return None
