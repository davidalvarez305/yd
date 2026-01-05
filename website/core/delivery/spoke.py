import requests
from website import settings
from core.billing.base import BillingServiceInterface

from django.http import HttpResponse
from django.utils import timezone
from django.core.files.base import ContentFile

from core.models import DriverStop, Event, Invoice, Lead, Message, User
from core.messaging import messaging_service
from core.logger import logger

class SpokeDeliveryService(BillingServiceInterface):
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