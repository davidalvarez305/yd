from django.utils.functional import LazyObject
from django.utils.module_loading import import_string
from website import settings

class MessagingService(LazyObject):
    def _setup(self):
        cls = import_string(settings.MESSAGING_SERVICE)
        self._wrapped = cls()

messaging_service = MessagingService()