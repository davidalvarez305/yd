import hashlib
from abc import ABC, abstractmethod
import logging
from core.http import BaseHttpClient

logger = logging.getLogger(__name__)

class ConversionService(ABC):
    def __init__(self):
        self.http = BaseHttpClient()

    @abstractmethod
    def _construct_payload(self, data: dict) -> dict:
        pass

    @abstractmethod
    def _get_endpoint(self) -> str:
        pass

    @abstractmethod
    def _get_service_name(self) -> str:
        """
        Returns a string identifying the name of the conversion service (e.g., 'facebook', 'google').
        Used for logging purposes.
        """
        pass

    def send_conversion(self, data: dict):
        payload = self._construct_payload(data)
        endpoint = self._get_endpoint()

        try:
            response = self.http.request(
                method="POST",
                url=endpoint,
                payload=payload,
                headers={"Content-Type": "application/json"},
                extra_log_fields={
                    "service_name": self._get_service_name()
                }
            )
            return response
        except Exception as err:
            logger.error(f"[{self._get_service_name()}] Failed to send conversion: {err}")
            raise

    def hash_to_sha256(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest() if value else None