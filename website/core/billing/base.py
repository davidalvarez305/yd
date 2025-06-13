from abc import ABC, abstractmethod

from django.http import HttpRequest

class BillingServiceInterface(ABC):
    @abstractmethod
    def handle_payment_webhook(self, request: HttpRequest) -> str:
        """
        Handles webhook call when payments are successfully completed or canceled.
        """
        pass

    @abstractmethod
    def handle_initiate_payment(self, request: HttpRequest):
        """
        Takes in a request and initiates a payment session/intent.
        """
        pass