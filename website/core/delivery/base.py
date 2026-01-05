from abc import ABC, abstractmethod

from django.http import HttpRequest

class DeliveryServiceInterface(ABC):
    @abstractmethod
    def handle_delivery_webhook(self, request: HttpRequest) -> str:
        """
        Handles webhook call when events are called on delivery.
        """
        pass