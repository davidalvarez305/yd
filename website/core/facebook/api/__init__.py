from django.utils.functional import LazyObject
from django.utils.module_loading import import_string

from website import settings

class FacebookAPIService(LazyObject):
    def _setup(self):
        cls = import_string(settings.FACEBOOK_API_SERVICE)

        self._wrapped = cls(
            api_version=settings.FACEBOOK_API_VERSION,
            app_id=settings.FACEBOOK_APP_ID,
            app_secret=settings.FACEBOOK_APP_SECRET,
        )

facebook_api_service = FacebookAPIService()