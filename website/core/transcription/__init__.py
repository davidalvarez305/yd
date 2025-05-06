from django.utils.functional import LazyObject
from django.utils.module_loading import import_string
from website import settings

class TranscriptionService(LazyObject):
    def _setup(self):
        cls = import_string(settings.TRANSCRIPTION_SERVICE)
        self._wrapped = cls()

transcription_service = TranscriptionService()