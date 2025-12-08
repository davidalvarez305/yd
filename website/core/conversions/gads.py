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
        now = datetime.now(tz=timezone.get_current_timezone())

        conversion_date_time = event_time.strftime("%Y-%m-%d %H:%M:%S%z")[:-2] + ":" + event_time.strftime("%z")[-2:]
        adjustment_date_time = now.strftime("%Y-%m-%d %H:%M:%S%z")[:-2] + ":" + now.strftime("%z")[-2:]

        payload = {
            "customer_id": self.customer_id,
            "conversion_action_id": self.conversion_actions.get(data.get("event_name")),
            "gclid": data.get("gclid"),
            "conversion_value": data.get("value"),
            "conversion_date_time": conversion_date_time,
            "adjustment_date_time": adjustment_date_time,
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
    
    import logging

# Setup logger
logger = logging.getLogger(__name__)

def retract_conversion(self, data: dict):
    # Step 1: Validate the data
    if not self._is_valid(data):
        logger.error("Data is invalid.")
        return None

    # Step 2: Construct payload
    try:
        logger.debug("Constructing payload...")
        payload = self._construct_payload(data)
        logger.debug(f"Payload constructed: {payload}")
    except Exception as e:
        logger.error(f"Error constructing payload: {e}")
        return None

    try:
        # Step 3: Prepare the conversion adjustment
        logger.debug("Preparing conversion adjustment...")
        conversion_adjustment_type_enum = self.client.enums.ConversionAdjustmentTypeEnum
        conversion_adjustment_type = conversion_adjustment_type_enum.RETRACTION.value

        conversion_adjustment = self.client.get_type("ConversionAdjustment")
        conversion_action_service = self.client.get_service("ConversionActionService")
        
        # Check if the customer_id and conversion_action_id exist in the payload
        if "customer_id" not in payload or "conversion_action_id" not in payload:
            logger.error("Missing customer_id or conversion_action_id in payload.")
            return None

        conversion_adjustment.conversion_action = conversion_action_service.conversion_action_path(
            payload["customer_id"], payload["conversion_action_id"]
        )

        conversion_adjustment.adjustment_type = conversion_adjustment_type
        conversion_adjustment.adjustment_date_time = payload["adjustment_date_time"]
        conversion_adjustment.order_id = str(payload["order_id"])

        # Ensure 'gclid' and 'conversion_date_time' exist
        if "gclid" not in payload or "conversion_date_time" not in payload:
            logger.error("Missing gclid or conversion_date_time in payload.")
            return None

        conversion_adjustment.gclid_date_time_pair.gclid = payload["gclid"]
        conversion_adjustment.gclid_date_time_pair.conversion_date_time = payload["conversion_date_time"]

        # Step 4: Upload the conversion adjustment
        logger.debug("Preparing request to upload conversion adjustment...")
        service = self.client.get_service("ConversionAdjustmentUploadService")
        request = self.client.get_type("UploadConversionAdjustmentsRequest")
        request.customer_id = payload["customer_id"]
        request.conversion_adjustments.append(conversion_adjustment)
        request.partial_failure = True

        # Step 5: Send the request
        logger.debug("Sending request to upload conversion adjustments...")
        response = service.upload_conversion_adjustments(request=request)

        # Step 6: Handle the response
        if response.partial_failure_error:
            for error in response.partial_failure_error.details:
                logger.error(f"Partial failure occurred: {error.message}")
        
        # Log the result if no error
        for result in response.results:
            logger.debug(f"Retracted conversion with order ID: {result.order_id} for conversion action: {result.conversion_action}")

        return response

    except Exception as e:
        logger.error(f"Error retracting conversion: {e}", exc_info=True)
        return None
