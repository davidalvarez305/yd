from django.utils.functional import LazyObject
from django.utils.module_loading import import_string

from website import settings

class ESignatureService(LazyObject):
    def _setup(self):
        cls = import_string(settings.E_SIGNATURE_SERVICE)
        
        self._wrapped = cls()

esignature_service = ESignatureService()