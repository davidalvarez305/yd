from django.utils.functional import LazyObject
from django.utils.module_loading import import_string

from website import settings

class ReviewsService(LazyObject):
    def _setup(self):
        cls = import_string(settings.REVIEWS_SERVICE)

        self._wrapped = cls(
            access_token=settings.GOOGLE_REFRESH_TOKEN,
            account_id=settings.GOOGLE_BUSINESS_PROFILE_ACCOUNT_ID,
            location_id=settings.GOOGLE_BUSINESS_PROFILE_LOCATION_ID,
        )

reviews_service = ReviewsService()