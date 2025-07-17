from django.utils.functional import LazyObject
from django.utils.module_loading import import_string

from website import settings

class GoogleAPIService(LazyObject):
    def _setup(self):
        cls = import_string(settings.GOOGLE_API_SERVICE)

        self._wrapped = cls()

google_api_service = GoogleAPIService()