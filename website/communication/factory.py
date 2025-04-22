from website import settings
from .messaging import MessagingServiceInterface, TwilioMessagingService
from twilio.rest import Client
from twilio.request_validator import RequestValidator

class MessagingServiceFactory:
    @staticmethod
    def get_service() -> MessagingServiceInterface:
        """
        Returns the appropriate messaging service instance
        based on the current environment.
        """
        if settings.DEBUG:
            return MessagingServiceFactory._create_twilio_service()
        return MessagingServiceFactory._create_twilio_service()

    @staticmethod
    def _create_twilio_service() -> TwilioMessagingService:
        client = Client(auth_token=settings.TWILIO_AUTH_TOKEN, account_sid=settings.TWILIO_ACCOUNT_SID)
        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        return TwilioMessagingService(client=client, validator=validator)
