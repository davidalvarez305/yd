from django.utils.functional import LazyObject
from django.utils.module_loading import import_string
from website import settings

class CallingService(LazyObject):
    def _setup(self):
        cls = import_string(settings.CALLING_SERVICE)
        self._wrapped = cls()

calling_service = CallingService()