from django.utils.functional import LazyObject
from django.utils.module_loading import import_string

from website import settings

class ReviewsService(LazyObject):
    def _setup(self):
        cls = import_string(settings.REVIEWS_SERVICE)

        self._wrapped = cls()

reviews_service = ReviewsService()