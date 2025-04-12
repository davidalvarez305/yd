import hashlib
import json
import requests
from django.utils.timezone import now
from website import settings
from core.models import Lead
from .models import ConversionLog
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Optional, Union
from abc import ABC, abstractmethod
from .enums import ConversionServiceType, ConversionEventType

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
    lead_id: Optional[str] = None


@dataclass
class FacebookCustomData:
    value: Optional[str] = None
    currency: Optional[str] = None
    event_source: Optional[str] = None
    lead_event_source: Optional[str] = None


@dataclass
class FacebookUserData:
    phone: Optional[str] = None
    email: Optional[str] = None
    external_id: Optional[str] = None
    fbp: Optional[str] = None
    fbc: Optional[str] = None


@dataclass
class FacebookEventData:
    event_name: Optional[str] = None
    event_time: Optional[int] = None
    event_id: Optional[str] = None
    action_source: Optional[str] = None
    event_source_url: Optional[str] = None
    user_data: Optional[FacebookUserData] = None
    custom_data: Optional[FacebookCustomData] = None


@dataclass
class FacebookPayload:
    data: List[FacebookEventData]


@dataclass
class GoogleUserAddress:
    sha256_full_name: Optional[str] = None
    sha256_street: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


@dataclass
class GoogleUserData:
    sha256_email_address: Optional[List[str]] = None
    sha256_phone_number: Optional[List[str]] = None
    address: Optional[List[GoogleUserAddress]] = None


@dataclass
class GoogleEventParamsLead:
    gclid: Optional[str] = None
    transaction_id: Optional[str] = None
    value: Optional[float] = None
    currency: Optional[str] = None
    campaign_id: Optional[str] = None
    campaign: Optional[str] = None
    source: Optional[str] = None
    medium: Optional[str] = None
    term: Optional[str] = None


@dataclass
class GoogleEventLead:
    name: Optional[str] = None
    params: Optional[GoogleEventParamsLead] = None


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
            response = requests.post(endpoint, json=asdict(payload), headers={"Content-Type": "application/json"})
            self._log_conversion(payload, response)
        except requests.exceptions.RequestException as err:
            self._log_conversion(payload, None, error={"error": str(err)})

    def _log_conversion(self, payload, response=None, error=None):
        payload_json = json.dumps(asdict(payload))

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

    def hash_to_sha256(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        return hashlib.sha256(value.encode('utf-8')).hexdigest()


class FacebookConversionService(ConversionService):
    def construct_payload(self) -> FacebookPayload:
        user_data = FacebookUserData(
            phone=self.hash_to_sha256(self.conversion_payload.phone_number),
            email=self.hash_to_sha256(self.conversion_payload.email),
            external_id=self.conversion_payload.external_id
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
            facebook_event_data.action_source = "system_generated"
            custom_data.lead_event_source = "YD Cocktails"
            custom_data.event_source = "crm"
        else:
            user_data.fbp = self.conversion_payload.client_id
            user_data.fbc = self.conversion_payload.client_id
            facebook_event_data.action_source = "website"

        return FacebookPayload(data=[facebook_event_data])

    def get_endpoint(self) -> str:
        return (
            f"https://graph.facebook.com/v20.0/"
            f"{settings.FACEBOOK_DATASET_ID}/events?access_token={settings.FACEBOOK_ACCESS_TOKEN}"
        )


class GoogleConversionService(ConversionService):
    def construct_payload(self) -> GooglePayload:
        event_params = GoogleEventParamsLead(
            gclid=self.conversion_payload.click_id,
            value=100.0,
            currency="USD",
            campaign_id=self.conversion_payload.campaign_id
        )

        google_event = GoogleEventLead(
            name=self.conversion_payload.conversion_event_type.value,
            params=event_params
        )

        user_data = GoogleUserData(
            sha256_email_address=[self.hash_to_sha256(self.conversion_payload.email)],
            sha256_phone_number=[self.hash_to_sha256(self.conversion_payload.phone_number)]
        )

        return GooglePayload(
            client_id=self.conversion_payload.client_id,
            user_id=self.conversion_payload.platform_id.name.lower(),
            events=[google_event],
            user_data=user_data
        )

    def get_endpoint(self) -> str:
        return (
            f"https://www.google-analytics.com/mp/collect"
            f"?measurement_id={settings.GOOGLE_ANALYTICS_ID}&api_secret={settings.GOOGLE_ANALYTICS_API_KEY}"
        )


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
        full_name=lead.full_name,
        lead_id=str(lead.id)
    )

    if conversion_payload.platform_id == ConversionServiceType.FACEBOOK:
        service = FacebookConversionService(conversion_payload)
    elif conversion_payload.platform_id == ConversionServiceType.GOOGLE:
        service = GoogleConversionService(conversion_payload)
    else:
        raise ValueError(f"Unsupported platform_id: {conversion_payload.platform_id}")

    service.send_conversion()