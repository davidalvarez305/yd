import requests
from requests.auth import HTTPBasicAuth

from django.http import HttpResponse
from django.core.exceptions import ValidationError

from core.delivery.base import DeliveryServiceInterface
from core.models import DriverStop
from core.logger import logger

CIRCUIT_BASE_URL = "https://api.getcircuit.com/public/v0.2b"

class SpokeDeliveryService(DeliveryServiceInterface):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def handle_delivery_webhook(self, request):
        payload = request.body

        try:
            event_type = payload.get('type')
            data = payload.get('data', {})

            if event_type == 'stop.allocated':
                return self._handle_stop_allocated(data)

            if event_type == 'stop.out_for_delivery':
                return self._handle_out_for_delivery(data)

            if event_type == 'stop.attempted_delivery':
                return self._handle_attempted_delivery(data)

            return HttpResponse(status=200)

        except Exception as e:
            logger.exception(str(e), exc_info=True)
            return HttpResponse(status=500)

    def _handle_stop_allocated(self, data):
        stop = DriverStop.objects.filter(external_id=data.get('id')).first()

        if not stop:
            return HttpResponse(status=400)
        
        # Message client alerting them of time window
        # Send client e-mail with reminer for delivery and pick-up policies

        return HttpResponse(status=200)

    def _handle_out_for_delivery(self, data):

        # Message client alerting them of time window
        # Send client e-mail with reminder about delays policy

        return HttpResponse(status=200)

    def _handle_attempted_delivery(self, data):
        return HttpResponse(status=200)
    
    def create_route(self, route_date, title, depot=None, drivers=None):
        if not route_date:
            raise ValidationError("route_date is required")

        if not title or not (1 <= len(title) <= 255):
            raise ValidationError("title must be between 1 and 255 characters")

        drivers = drivers or []

        if len(drivers) > 50:
            raise ValidationError("drivers list cannot exceed 50 items")

        payload = {
            "title": title,
            "starts": {
                "day": route_date.day,
                "month": route_date.month,
                "year": route_date.year,
            },
            "drivers": drivers,
        }

        if depot:
            payload["depot"] = depot

        response = requests.post(
            f"{CIRCUIT_BASE_URL}/plans",
            auth=HTTPBasicAuth(self.api_key, ""),
            json=payload,
            timeout=15,
        )

        response.raise_for_status()

        return response.json()