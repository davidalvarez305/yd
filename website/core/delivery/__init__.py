from django.utils.functional import LazyObject
from django.utils.module_loading import import_string

from website import settings

class DeliveryService(LazyObject):
    def _setup(self):
        cls = import_string(settings.DELIVERY_SERVICE)

        self._wrapped = cls(api_key=settings.SPOKE_API_KEY)

delivery_service = DeliveryService()