from enum import Enum
from website import settings

class MessagingProvider(Enum):
    TWILIO = "twilio"

class TwilioWebhookEvents(Enum):
    INITIATED = "initiated"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    NO_ANSWER = "no-answer"
    BUSY = "busy"
    FAILED = "failed"
    CANCELED = "canceled"

    @classmethod
    def all(cls):
        return [e.value for e in cls]

    @classmethod
    def outbound(cls):
        return 'initiated ringing answered completed'

class TwilioWebhookCallbacks(Enum):
    INBOUND = "/communication/calls/inbound"
    STATUS = "/communication/calls/end/status"
    RECORDING = "/communication/calls/end/recording"
    OUTBOUND = "/communication/calls/outbound"
    OUTBOUND_STATUS = "/communication/calls/outbound/status"
    MESSAGE_STATUS_CALLBACK = "/communication/message/end/status"

    @classmethod
    def get_full_url(cls, endpoint):
        base_url = settings.ROOT_DOMAIN

        if settings.DEBUG:
            base_url = "https://" + settings.NGROK_HOST
        
        return base_url + endpoint