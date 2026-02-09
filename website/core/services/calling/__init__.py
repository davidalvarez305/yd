from django.utils.functional import LazyObject
from django.utils.module_loading import import_string

from website import settings
from core.transcription import TranscriptionService

class CallingService(LazyObject):
    def _setup(self):
        cls = import_string(settings.CALLING_SERVICE)
        
        self._wrapped = cls(
            account_sid=settings.TWILIO_ACCOUNT_SID,
            auth_token=settings.TWILIO_AUTH_TOKEN,
            transcription_service=TranscriptionService()
        )

calling_service = CallingService()