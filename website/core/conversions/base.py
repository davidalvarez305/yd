import hashlib
import json
import requests
from django.utils.timezone import now
from .models import ConversionLog
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class ConversionService(ABC):
    def __init__(self, conversion_data: dict):
        """
        conversion_data: Dictionary containing all required fields for a conversion.
        """
        self.conversion_data = conversion_data

    @abstractmethod
    def construct_payload(self) -> dict:
        """
        Constructs the appropriate payload for the conversion event.
        """
        pass

    def send_conversion(self):
        """
        Constructs and sends the conversion event to the platform.
        """
        payload = self.construct_payload()
        endpoint = self.get_endpoint()
        self._send_request(endpoint, payload)

    @abstractmethod
    def get_endpoint(self) -> str:
        """
        Returns the API endpoint URL for the conversion event.
        """
        pass

    def _send_request(self, endpoint: str, payload: dict):
        """
        Sends the payload to the specified endpoint.
        """
        try:
            response = requests.post(
                endpoint, 
                json=payload, 
                headers={"Content-Type": "application/json"}
            )
            self._log_conversion(payload, response)
        except requests.exceptions.RequestException as err:
            logger.error(f"Failed to send conversion: {err}")
            self._log_conversion(payload, None, error={"error": str(err)})

    def _log_conversion(self, payload: dict, response=None, error=None):
        """
        Logs the conversion attempt, its payload, and the response.
        """
        payload_json = json.dumps(payload)

        if response:
            response_json = json.dumps(response.json())
            status_code = response.status_code
        else:
            response_json = json.dumps(error)
            status_code = 500

        ConversionLog.objects.create(
            date_created=now(),
            endpoint=self.get_endpoint(),
            payload=payload_json,
            status_code=status_code,
            response=response_json
        )

    def hash_to_sha256(self, value: str) -> str:
        """
        Hashes a string using SHA-256.
        """
        if not value:
            return None
        return hashlib.sha256(value.encode("utf-8")).hexdigest()