import hashlib
from abc import ABC, abstractmethod
from core.http import BaseHttpClient

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
            print(f'INVALID DATA: {data}')
            return

        try:
            response = self.http.request(
                method="POST",
                url=endpoint,
                payload=payload,
                headers={"Content-Type": "application/json"},
                extra_log_fields={"service_name": self._get_service_name()}
            )
            return response
        except Exception as err:
            print(f'ERROR SENDING CONV: {err}')
            raise

    def hash_to_sha256(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest() if value else None