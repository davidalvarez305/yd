import hashlib
import json
import requests
from django.utils.timezone import now
from website.website import settings
from website.core.models import Lead
from .models import ConversionLog
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Union
from abc import ABC, abstractmethod

class ConversionServiceType(Enum):
    GOOGLE = 1
    FACEBOOK = 2

class ConversionEventType(Enum):
    FormSubmission = "generate_lead"
    LeadAd = "generate_lead"
    WebsiteCall = "Website call"
    EventBooking = "event"

@dataclass
class ConversionPayload:
    conversion_event_type: Optional[ConversionEventType] = None
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
        payload = self.construct_payload()
        endpoint = self.get_endpoint()
        self._send_request(endpoint, payload)

    def get_endpoint(self) -> str:
        raise NotImplementedError("Subclasses must implement this method to provide the endpoint.")

    def _send_request(self, endpoint, payload):
        try:
            response = requests.post(endpoint, json=payload.__dict__, headers={"Content-Type": "application/json"})
            self._log_conversion(payload, response)
        except requests.exceptions.RequestException as err:
            self._log_conversion(payload, None, error={"error": str(err)})

    def _log_conversion(self, payload, response=None, error=None):
        if not isinstance(payload, str):
            payload = json.dumps(payload, default=lambda o: o.__dict__)

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
        if value is None:
            return ''
        return hashlib.sha256(value.encode('utf-8')).hexdigest()

class FacebookConversionService(ConversionService):
    def construct_payload(self) -> FacebookPayload:
        user_data = FacebookUserData(
            phone=self.hash_to_sha256(self.conversion_payload.phone_number),
            email=self.hash_to_sha256(self.conversion_payload.email),
            external_id=self.conversion_payload.external_id,
        )
        custom_data = FacebookCustomData(
            value="100",
            currency="USD"
        )
        facebook_event_data = FacebookEventData(
            event_name=self.conversion_payload.conversion_event_type.value,
            event_time=int(now().timestamp()),
            user_data=user_data,
            custom_data=custom_data
        )

        if self.conversion_payload.lead_id:
            user_data.lead_id = self.conversion_payload.lead_id
            facebook_event_data.action_source = "system generated"
            custom_data.lead_event_source = "YD Cocktails"
            custom_data.event_source = "crm"
        else:
            user_data.fbp = self.conversion_payload.client_id
            user_data.fbc = self.conversion_payload.client_id
            facebook_event_data.action_source = "website"

        data = [facebook_event_data]

        return FacebookPayload(data=data)

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
            name=self.conversion_payload.conversion_event_type.value,
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

def report_conversion(conversion_event_type: ConversionEventType, lead: Lead):
    conversion_payload = ConversionPayload(
        conversion_event_type=conversion_event_type,
        platform_id=lead.marketing.platform_id,
        campaign_id=lead.marketing.campaign.campaign_id,
        click_id=lead.marketing.click_id,
        client_id=lead.marketing.client_id,
        external_id=lead.marketing.external_id,
        phone_number=lead.phone_number,
        email=lead.email,
        full_name=lead.full_name
    )
    conversion_service: ConversionService

    if conversion_payload.platform_id == ConversionServiceType.FACEBOOK:
        conversion_service = FacebookConversionService(conversion_payload)
    elif conversion_payload.platform_id == ConversionServiceType.GOOGLE:
        conversion_service = GoogleConversionService(conversion_payload)
    else:
        raise ValueError(f"Unsupported platform_id: {conversion_payload.platform_id}")

    conversion_service.send_conversion()