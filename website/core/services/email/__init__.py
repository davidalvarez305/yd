from django.utils.functional import LazyObject
from django.utils.module_loading import import_string
from website import settings

class EmailService(LazyObject):
    def _setup(self):
        cls = import_string(settings.EMAIL_SERVICE)
        self._wrapped = cls()

email_service = EmailService()