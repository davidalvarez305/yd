from enum import Enum
from website import settings

class MessagingProvider(Enum):
    TWILIO = "twilio"

class TwilioWebhookEvents(Enum):
    COMPLETED = "completed"
    NO_ANSWER = "no-answer"
    BUSY = "busy"
    FAILED = "failed"

    @classmethod
    def all(cls):
        return [e.value for e in cls]

class TwilioWebhookCallbacks(Enum):
    INBOUND = "/communication/calls/inbound"
    STATUS = "/communication/calls/status"
    OUTBOUND = "/communication/calls/outbound"
    RECORDING = "/communication/calls/recording"

    @classmethod
    def get_full_url(cls, endpoint):
        base_url = settings.ROOT_DOMAIN
        return base_url + endpoint