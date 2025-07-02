import hashlib
from abc import ABC, abstractmethod
from core.http.base import BaseHttpClient
from core.logger import logger

class ConversionService(ABC):
    def __init__(self, **options):
        self.http = BaseHttpClient()
        self.options = options

    @abstractmethod
    def _construct_payload(self, data: dict) -> dict:
        pass

    @abstractmethod
    def _is_valid(self, data: dict) -> dict:
        pass

    @abstractmethod
    def _get_endpoint(self) -> str:
        pass

    @abstractmethod
    def _get_service_name(self) -> str:
        """
        Returns a string identifying the name of the conversion service (e.g., 'facebook', 'google').
        """
        pass

    def send_conversion(self, data: dict):
        payload = self._construct_payload(data)
        endpoint = self._get_endpoint()

        if not self._is_valid(data):
            return

        try:
            response = self.http.request(
                method="POST",
                url=endpoint,
                payload=payload,
                headers={"Content-Type": "application/json"}
            )

            return response
        except Exception as e:
            logger.error(e, exc_info=True, stack_info=True)
            raise Exception(str(e))

    def hash_to_sha256(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest() if value else None