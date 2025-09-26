from django.utils.functional import LazyObject
from django.utils.module_loading import import_string

from website import settings

class CallTrackingService(LazyObject):
    def _setup(self):
        cls = import_string(settings.CALL_TRACKING_SERVICE)
        
        self._wrapped = cls()

call_tracking_service = CallTrackingService()