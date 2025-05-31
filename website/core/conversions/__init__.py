from django.utils.module_loading import import_string
from django.conf import settings

class ConversionServiceLoader:
    def __init__(self):
        self._instances = {}

    def get(self, key):
        """Get the service instance either from settings or internal registry."""
        if key in self._instances:
            return self._instances[key]

        if key in settings.CONVERSION_SERVICES:
            config = settings.CONVERSION_SERVICES[key]
            cls = import_string(config["BACKEND"])
            options = config.get("OPTIONS", {})
            instance = cls(**options)
        else:
            raise ValueError(f"No conversion service found for key '{key}'.")

        self._instances[key] = instance
        return instance

    def all_services(self):
        """Return all initialized service instances."""
        keys = set(settings.CONVERSION_SERVICES.keys())
        return [self.get(key) for key in keys]

    def send_conversion(self, data: dict):
        """Send the conversion data to all registered services."""
        for service in self.all_services():
            service.send_conversion(data)

conversion_service = ConversionServiceLoader()