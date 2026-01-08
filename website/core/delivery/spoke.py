import requests
from core.delivery.base import DeliveryServiceInterface

from django.http import HttpResponse
from django.core.exceptions import ValidationError

from core.models import DriverStop
from core.messaging import messaging_service
from core.logger import logger

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
    
    def create_route(self, data: dict):
        route_date = data.get('route_date')
        if not route_date:
            raise ValidationError('Route date not found in data dictionary.')

        data = {
            "title": "Test",
            "starts": {
                "day": route_date.day,
                "month": route_date.month,
                "year": route_date.year,
            }
        }

        resp = requests.post(
            "https://api.getcircuit.com/public/v0.2b/plans",
            auth=HTTPBasicAuth(self.api_key, ""),
            json=data,
        )

        plan = resp.json()

        stops = []
        for stop in data.get('stops'):
            address = stop.address

            stop_payload = {
                "address": {
                    "addressName": stop.contact_name,
                    "addressLineOne": address.address_line_1,
                    "addressLineTwo": address.address_line_2 or "",
                    "city": address.city,
                    "state": address.state_code,
                    "zip": address.postal_code,
                    "country": "US",
                },
                "recipient": {
                    "externalId": recipient_id,
                    "name": stop.contact_name,
                    "phone": stop.contact_phone,
                    "email": stop.user.email if stop.user and stop.user.email else "",
                },
                "activity": stop.stop_type.lower(),
                "packageCount": 1,
                "circuitClientId": circuit_client_id,
                "notes": f"Order {stop.order.code}",
                "proofOfAttemptRequirements": {
                    "enabled": True,
                },
                "customProperties": {
                    "order_id": str(stop.order_id),
                    "driver_stop_id": str(stop.driver_stop_id),
                },
            }

            # Optional timing window
            if stop.start_time and stop.end_time:
                start = stop.start_time
                end = stop.end_time

                stop_payload["timing"] = {
                    "earliestAttemptTime": {
                        "hour": start.hour,
                        "minute": start.minute,
                    },
                    "latestAttemptTime": {
                        "hour": end.hour,
                        "minute": end.minute,
                    },
                    "estimatedAttemptDuration": max(
                        int((end - start).total_seconds() // 60), 1
                    ),
                }

            stops.append(stop_payload)

        stops_resp = requests.post(
            f'https://api.getcircuit.com/public/v0.2b/{plan.get('id')}/stops:import',
            auth=HTTPBasicAuth(self.api_key, ""),
            json=stops,
        )

        created_stops = stops_resp.json()