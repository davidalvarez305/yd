from enum import Enum

class MessagingProvider(Enum):
    TWILIO = "twilio"

class TwillWebhookEvents(Enum):
    COMPLETED = "completed"
    NO_ANSWER = "no-answer"
    BUSY = "busy"
    FAILED = "failed"

    @classmethod
    def all(cls):
        return [e.value for e in cls]

    @classmethod
    def callback_handlers(cls):
        return {
            cls.COMPLETED.value: "/communication/calls/completed/",
            cls.NO_ANSWER.value: "/communication/calls/no-answer/",
            cls.BUSY.value: "/communication/calls/busy/",
            cls.FAILED.value: "/communication/calls/failed/",
        }