import hashlib
import json
import requests
from django.utils.timezone import now
from website.website import settings
from .models import ConversionLog
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Union
from abc import ABC, abstractmethod

class ConversionServiceType(Enum):
    GOOGLE = 1
    FACEBOOK = 2

class ConversionEventType(Enum):
    FormSubmission = 1
    LeadAd = 2
    WebsiteCall = 3
    EventBooking = 4

@dataclass
class ConversionPayload:
    conversion_event_type: Optional[str] = None
    platform_id: Optional[ConversionServiceType] = None
    campaign_id: Optional[str] = None
    click_id: Optional[str] = None
    client_id: Optional[str] = None
    external_id: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None

@dataclass
class FacebookUserData:
    phone: Optional[str] = None
    email: Optional[str] = None
    external_id: Optional[str] = None

@dataclass
class FacebookCustomData:
    value: Optional[str] = None
    currency: Optional[str] = None

@dataclass
class FacebookEventData:
    event_name: Optional[str] = None
    event_time: Optional[int] = None
    user_data: Optional[FacebookUserData] = None
    custom_data: Optional[FacebookCustomData] = None

@dataclass
class FacebookPayload:
    data: List[FacebookEventData]

@dataclass
class GoogleEventParamsLead:
    gclid: Optional[str] = None
    value: Optional[float] = None
    currency: Optional[str] = None

@dataclass
class GoogleEventLead:
    name: Optional[str] = None
    params: Optional[GoogleEventParamsLead] = None

@dataclass
class GoogleUserData:
    sha256_email_address: Optional[List[str]] = None
    sha256_phone_number: Optional[List[str]] = None

@dataclass
class GooglePayload:
    client_id: Optional[str] = None
    user_id: Optional[str] = None
    events: Optional[List[GoogleEventLead]] = None
    user_data: Optional[GoogleUserData] = None

class ConversionService(ABC):
    def __init__(self, conversion_payload: ConversionPayload):
        self.conversion_payload = conversion_payload
    
    @abstractmethod
    def construct_payload(self) -> Union[GooglePayload, FacebookPayload]:
        pass
    
    def send_conversion(self):
        """Handles sending the conversion request and logging the result."""
        payload = self.construct_payload()  # Construct the payload when sending the conversion
        endpoint = self.get_endpoint()
        self._send_request(endpoint, payload)
    
    def get_endpoint(self) -> str:
        """This method should be overridden by subclasses to return the correct endpoint."""
        raise NotImplementedError("Subclasses must implement this method to provide the endpoint.")
    
    def _send_request(self, endpoint, payload):
        """Send the conversion payload to the respective service's endpoint."""
        try:
            response = requests.post(endpoint, json=payload.to_dict(), headers={"Content-Type": "application/json"})
            self._log_conversion(payload, response)
        except requests.exceptions.RequestException as err:
            self._log_conversion(payload, None, error={"error": str(err)})

    def _log_conversion(self, payload, response=None, error=None):
        """Log the conversion request and response to the database."""
        if not isinstance(payload, str):
            payload = json.dumps(payload)
        
        if response:
            response_json = json.dumps(response.json())
            status_code = response.status_code
        else:
            response_json = json.dumps(error)
            status_code = 500
        
        ConversionLog.objects.create(
            date_created=now(),
            endpoint=self.get_endpoint(),
            payload=payload,
            status_code=status_code,
            response=response_json
        )

    def hash_to_sha256(self, value: str) -> str:
        """Hash the input value using SHA-256."""
        if value is None:
            return ''
        return hashlib.sha256(value.encode('utf-8')).hexdigest()

class FacebookConversionService(ConversionService):
    def construct_payload(self) -> FacebookPayload:
        facebook_event_data = FacebookEventData(
            event_name=self.conversion_payload.conversion_event_type,
            event_time=int(now().timestamp()),
            user_data=FacebookUserData(
                phone=self.hash_to_sha256(self.conversion_payload.phone_number),
                email=self.hash_to_sha256(self.conversion_payload.email),
                external_id=self.conversion_payload.external_id
            ),
            custom_data=FacebookCustomData(
                value="100",
                currency="USD"
            )
        )
        return FacebookPayload(data=[facebook_event_data])

    def get_endpoint(self) -> str:
        return f"https://graph.facebook.com/v20.0/{settings.FACEBOOK_DATASET_ID}/events?access_token={settings.FACEBOOK_ACCESS_TOKEN}"

class GoogleConversionService(ConversionService):
    def construct_payload(self) -> GooglePayload:
        google_event_params = GoogleEventParamsLead(
            gclid=self.conversion_payload.click_id,
            value=100.0,
            currency="USD"
        )
        google_event = GoogleEventLead(
            name="generate_lead",
            params=google_event_params
        )
        google_user_data = GoogleUserData(
            sha256_email_address=[self.hash_to_sha256(self.conversion_payload.email)],
            sha256_phone_number=[self.hash_to_sha256(self.conversion_payload.phone_number)]
        )
        return GooglePayload(
            client_id=self.conversion_payload.client_id,
            user_id=self.conversion_payload.platform_id.value,
            events=[google_event],
            user_data=google_user_data
        )

    def get_endpoint(self) -> str:
        return f"https://www.google-analytics.com/mp/collect?measurement_id={settings.GOOGLE_ANALYTICS_ID}&api_secret={settings.GOOGLE_ANALYTICS_API_KEY}"

def report_conversion(conversion_payload: ConversionPayload):
    """Directly create the correct service and report the conversion."""
    conversion_service: ConversionService
    
    if conversion_payload.platform_id == ConversionServiceType.FACEBOOK:
        conversion_service = FacebookConversionService(conversion_payload)
    elif conversion_payload.platform_id == ConversionServiceType.GOOGLE:
        conversion_service = GoogleConversionService(conversion_payload)
    else:
        raise ValueError(f"Unsupported platform_id: {conversion_payload.platform_id}")

    conversion_service.send_conversion()