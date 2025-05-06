from django.utils.module_loading import import_string
from django.conf import settings

class ConversionServiceLoader:
    def __init__(self):
        self._instances = {}
        self._registry = {}

    def register(self, key, cls):
        """Register a conversion service class manually or via decorator."""
        self._registry[key] = cls

    def get(self, key):
        """Get the service instance either from settings or internal registry."""
        if key in self._instances:
            return self._instances[key]

        if key in settings.CONVERSION_SERVICES:
            config = settings.CONVERSION_SERVICES[key]
            cls = import_string(config["BACKEND"])
            options = config.get("OPTIONS", {})
            instance = cls(**options)
        elif key in self._registry:
            cls = self._registry[key]
            instance = cls()
        else:
            raise ValueError(f"No conversion service found for key '{key}'.")

        self._instances[key] = instance
        return instance