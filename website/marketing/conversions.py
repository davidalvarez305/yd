from abc import ABC, abstractmethod
import requests
import json
from django.utils.timezone import now
from website.website import settings
from .models import ConversionLog
from enum import Enum

class ConversionServiceType(Enum):
    GOOGLE = 1
    FACEBOOK = 2

class ConversionService(ABC):
    def __init__(self, conversion_service_type, endpoint):
        if not conversion_service_type or not endpoint:
            raise ValueError("conversion_service_type, and endpoint are required for initialization.")

        self.conversion_service_type = conversion_service_type
        self.endpoint = endpoint

    @abstractmethod
    def send_form_conversion(self, payload):
        pass

    @abstractmethod
    def send_phone_conversion(self, payload):
        pass

    def log_conversion(self, endpoint, payload, status_code, response):
        if not isinstance(payload, str):
            payload = json.dumps(payload)
        
        try:
            response_json = json.dumps(response.json())
        except ValueError:
            response_json = json.dumps({"error": response.text})

        ConversionLog.objects.create(
            date_created=now(),
            endpoint=endpoint,
            payload=payload,
            status_code=status_code,
            response=response_json,
            conversion_service_type_id=self.conversion_service_type.value
        )

class GoogleConversionService(ConversionService):
    def __init__(self, conversion_service_type, endpoint):
        super().__init__(conversion_service_type, endpoint)

    def send_form_conversion(self, payload):
        try:
            url = self.endpoint
            response = requests.post(url=url, json=payload, headers={"Content-Type": "application/json"})

            self.log_conversion(url, payload, response.status_code, response)

        except requests.exceptions.RequestException as err:
            self.log_conversion(url, payload, 500, {"error": str(err)})
            return f"Request error: {err}"

    def send_phone_conversion(self, payload):
        pass

class FacebookConversionService(ConversionService):
    def __init__(self, conversion_service_type, endpoint):
        super().__init__(conversion_service_type, endpoint)

    def send_form_conversion(self, payload):
        try:
            response = requests.post(self.endpoint, json=payload)

            self.log_conversion(self.endpoint, payload, response.status_code, response)

        except requests.exceptions.RequestException as err:
            self.log_conversion(self.endpoint, payload, 500, {"error": str(err)})

    def send_phone_conversion(self, payload):
        pass

def initialize_facebook_conversion_service():
    endpoint = f"https://graph.facebook.com/v20.0/{settings.FACEBOOK_DATASET_ID}/events?access_token={settings.FACEBOOK_ACCESS_TOKEN}"
    return FacebookConversionService(
        conversion_service_type=ConversionServiceType.FACEBOOK,
        endpoint=endpoint
    )

def initialize_google_conversion_service():
    endpoint = f"https://www.google-analytics.com/mp/collect?measurement_id={settings.GOOGLE_ANALYTICS_ID}&api_secret={settings.GOOGLE_ANALYTICS_API_KEY}"
    return GoogleConversionService(
        conversion_service_type=ConversionServiceType.GOOGLE,
        endpoint=endpoint
    )
