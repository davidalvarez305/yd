from django.utils.functional import LazyObject
from django.utils.module_loading import import_string

from website import settings

class BillingService(LazyObject):
    def _setup(self):
        cls = import_string(settings.BILLING_SERVICE)

        self._wrapped = cls(
            api_key=settings.STRIPE_API_KEY,
            webhook_secret=settings.STRIPE_WEBHOOK_SECRET,
        )

billing_service = BillingService()