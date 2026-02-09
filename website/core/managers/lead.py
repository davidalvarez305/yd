import json
from urllib.parse import parse_qsl, urlparse
from django.db import transaction
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from dataclasses import dataclass
from typing import Optional
from django.core.exceptions import ValidationError

from core.models import Ad, AdCampaign, AdGroup, AdPlatform, AdPlatformChoices, ConversionTypeChoices, Event, LandingPage, LandingPageConversion, LeadMarketing, LeadMarketingMetadata, LeadStatus, LeadStatusChoices, Lead, LeadStatusHistory, Message, SessionMapping, TrackingPhoneCall, TrackingPhoneCallMetadata, TrackingTextMessage, TrackingTextMessageMetadata, User
from core.conversions import conversion_service
from core.utils import create_ad_from_params, format_text_message, get_session_data, is_google_ads_call_asset, parse_google_ads_cookie
from core.messaging import messaging_service
from website import settings
from core.helpers.marketing import MarketingHelper

@dataclass
class LeadTransitionContext:
    user: Optional[User] = None
    event: Optional[Event] = None
    source: str = "system"

class InvalidLeadTransitionError(ValidationError):
    """Raised when an invalid lead status transition is attempted."""
    pass

class LeadStateManager:
    TRANSITIONS = {
        LeadStatusChoices.LEAD_CREATED: {
            LeadStatusChoices.INVOICE_SENT,
            LeadStatusChoices.ARCHIVED,
        },
        LeadStatusChoices.INVOICE_SENT: {
            LeadStatusChoices.EVENT_BOOKED,
            LeadStatusChoices.ARCHIVED,
        },
        LeadStatusChoices.EVENT_BOOKED: {
            LeadStatusChoices.ARCHIVED,
        },
        LeadStatusChoices.ARCHIVED: set(),
    }

    TERMINAL_STATUSES = {
        LeadStatusChoices.ARCHIVED,
    }

    def __init__(self, lead: Lead):
        self.lead = lead

    @property
    def current_status(self) -> LeadStatusChoices | None:
        if not self.lead.lead_status:
            return None
        return LeadStatusChoices(self.lead.lead_status.status)

    def allowed_transitions(self) -> set[LeadStatusChoices]:
        if not self.current_status:
            return set()
        return self.TRANSITIONS.get(self.current_status, set())

    def can_transition_to(self, new_status: LeadStatusChoices) -> bool:
        if not self.current_status:
            return True
        return new_status in self.allowed_transitions()

    @transaction.atomic
    def transition_to(self, status: str, context: LeadTransitionContext | None = None):
        context = context or LeadTransitionContext()

        if self.current_status in self.TERMINAL_STATUSES:
            raise InvalidLeadTransitionError(
                f"Lead already terminal ({self.current_status})"
            )

        if self.current_status and not self.can_transition_to(status):
            raise InvalidLeadTransitionError(
                f"Cannot transition lead from '{self.current_status}' to '{status}'"
            )

        lead_status = LeadStatus.objects.get(status=status)

        LeadStatusHistory.objects.create(lead=self.lead, lead_status=lead_status)

        self._run_hooks(status, context)

    def _run_hooks(self, status: LeadStatusChoices, context: LeadTransitionContext):
        match status:
            case LeadStatusChoices.LEAD_CREATED:
                self._on_lead_created(context)
            case LeadStatusChoices.INVOICE_SENT:
                self._on_invoice_sent(context)
            case LeadStatusChoices.EVENT_BOOKED:
                self._on_event_booked(context)
            case LeadStatusChoices.ARCHIVED:
                self._on_archived(context)
    
    def book_event(self, event: Event):
        context = {
            'event': event,
            'source': 'webhook',
        }
        self.transition_to(LeadStatusChoices.EVENT_BOOKED, context=context)
    
    def handle_lead_creation_via_instant_form(self, data, entry):
        marketing, _ = LeadMarketing.objects.get_or_create(
                instant_form_lead_id=entry.get('leadgen_id'),
                defaults={
                    'lead': self.lead,
                    'instant_form_id': data.get('form_id'),
                }
            )

        if not data.get('is_organic'):
            ad_platform = AdPlatform.objects.get(platform=AdPlatformChoices.FACEBOOK)
            ad_campaign, _ = AdCampaign.objects.get_or_create(
                ad_campaign_id=data.get('campaign_id'),
                defaults={
                    'name': data.get('campaign_name'),
                    'ad_platform': ad_platform,
                }
            )
            ad_group, _ = AdGroup.objects.get_or_create(
                ad_group_id=data.get('adset_id'),
                defaults={
                    'name': data.get('adset_name'),
                    'ad_campaign': ad_campaign,
                }
            )
            ad, _ = Ad.objects.get_or_create(
                ad_id=data.get('ad_id'),
                defaults={
                    'name': data.get('ad_name'),
                    'ad_group': ad_group,
                }
            )
            
            marketing.ad = ad
            marketing.save()

        metadata = [
            {
                'key': 'source',
                'value': data.get('platform'),
            },
            {
                'key': 'medium',
                'value': 'paid',
            },
            {
                'key': 'channel',
                'value': 'social',
            }
        ]

        for data in metadata:
            entry = LeadMarketingMetadata(
                key=data.get('key'),
                value=data.get('value'),
                lead_marketing=marketing,
            )
            entry.save()
            
        self.transition_to(LeadStatusChoices.LEAD_CREATED)
    
    def handle_lead_creation_via_form(self, request: HttpRequest):
        marketing_helper = MarketingHelper(request=request)
        lead_marketing = LeadMarketing.objects.create(lead=self.lead)
        if not request.user.is_authenticated:
            marketing_helper = MarketingHelper(request)
            lead_marketing.ip = marketing_helper.ip
            lead_marketing.external_id = marketing_helper.external_id
            lead_marketing.user_agent = marketing_helper.user_agent
            lead_marketing.ad = marketing_helper.ad
            lead_marketing.save()
            
            for key, value in marketing_helper.metadata.items():
                LeadMarketingMetadata.objects.create(
                    key=key,
                    value=value,
                    lead_marketing=self.lead.lead_marketing,
                )
            
            lp = self.request.session.get("landing_page_id")
            if lp:
                landing_page = LandingPage.objects.filter(pk=lp).first()
                if landing_page:
                    conversion = LandingPageConversion(
                        lead=self.lead,
                        landing_page=landing_page,
                    )
                    conversion.save()
        
        self.transition_to(LeadStatusChoices.LEAD_CREATED)
    
    def handle_lead_creation_via_tracking_message(self, tracking_message: TrackingPhoneCall):
        message_metadata = TrackingTextMessageMetadata.objects.filter(tracking_message=tracking_message)
        metadata = message_metadata.filter(key="custom").first()

        if metadata:
            try:
                params = json.loads(metadata.value) or {}

                lp = params.get("calltrk_landing")
                if lp:
                    params |= dict(parse_qsl(urlparse(self.landing_page).query))(lp)

                external_id = params.get(settings.TRACKING_COOKIE_NAME)
                if external_id:
                    session_mapping = SessionMapping.objects.filter(external_id=external_id).first()
                    if session_mapping:
                        session = get_session_data(session_key=session_mapping.session_key)

                        self.lead.lead_marketing.ip = session.get('ip')
                        self.lead.lead_marketing.user_agent = session.get('user_agent')
                        self.lead.lead_marketing.external_id = external_id
                        self.lead.lead_marketing.ad = create_ad_from_params(params=params)
                        self.lead.lead_marketing.save()
                        self.lead.lead_marketing.assign_visits()

                        landing_page_id = session.get('landing_page_id')
                        if landing_page_id:
                            landing_page = LandingPage.objects.filter(pk=landing_page_id).first()
                            if landing_page:
                                conversion = LandingPageConversion(
                                    lead=self.lead,
                                    landing_page=landing_page,
                                    conversion_type=ConversionTypeChoices.TEXT_MESSAGE
                                )
                                conversion.save()

                for key, value in params.items():
                    LeadMarketingMetadata.objects.create(
                        key=key,
                        value=value,
                        lead_marketing=self.lead.lead_marketing,
                    )
            except (TypeError, json.JSONDecodeError):
                print("Failed to load params")

        self.transition_to(LeadStatusChoices.LEAD_CREATED)

    def handle_lead_creation_via_tracking_call(self, tracking_message: TrackingTextMessage):
        phone_call_metadata = TrackingPhoneCallMetadata.objects.filter(tracking_message=tracking_message)
        metadata = phone_call_metadata.filter(key="custom").first()

        if metadata:
            try:
                params = json.loads(metadata.value) or {}

                lp = params.get("calltrk_landing")
                if lp:
                    params |= dict(parse_qsl(urlparse(self.landing_page).query))(lp)

                external_id = params.get(settings.TRACKING_COOKIE_NAME)
                if external_id:
                    session_mapping = SessionMapping.objects.filter(external_id=external_id).first()
                    if session_mapping:
                        session = get_session_data(session_key=session_mapping.session_key)

                        self.lead.lead_marketing.ip = session.get('ip')
                        self.lead.lead_marketing.user_agent = session.get('user_agent')
                        self.lead.lead_marketing.external_id = external_id
                        self.lead.lead_marketing.ad = create_ad_from_params(params=params)
                        self.lead.lead_marketing.save()
                        self.lead.lead_marketing.assign_visits()

                        landing_page_id = session.get('landing_page_id')
                        if landing_page_id:
                            landing_page = LandingPage.objects.filter(pk=landing_page_id).first()
                            if landing_page:
                                conversion = LandingPageConversion(
                                    lead=self.lead,
                                    landing_page=landing_page,
                                    conversion_type=ConversionTypeChoices.PHONE_CALL
                                )
                                conversion.save()

                for key, value in params.items():
                    LeadMarketingMetadata.objects.create(
                        key=key,
                        value=value,
                        lead_marketing=self.lead.lead_marketing,
                    )
            except (TypeError, json.JSONDecodeError):
                print("Failed to load params")

        self.transition_to(LeadStatusChoices.LEAD_CREATED)
    
    def _on_lead_created(self, context: LeadTransitionContext):

        if settings.DEBUG:
            return
        
        # Notify Users
        users = User.objects.filter(is_superuser=True)

        text_content = "\n".join([
            f"NEW LEAD:",
            f"FULL NAME: {self.lead.full_name}",
            f"PHONE NUMBER: {self.lead.phone_number}",
            f"MESSAGE: {str(self.lead.message)}",
            f"LINK: {settings.ROOT_DOMAIN + reverse('lead_detail', kwargs={'pk': self.lead.pk})}",
        ])

        for user in users:
            message = Message(
                text=format_text_message(text_content),
                text_from=settings.COMPANY_PHONE_NUMBER,
                text_to=user.forward_phone_number,
                is_inbound=False,
                status='sent',
                is_read=True,
            )
            resp = messaging_service.send_text_message(message=message)
            message.external_id = resp.sid
            message.status = resp.status
            message.save()

        # Do not report conversions for call asset calls
        phone_call = self.lead.phone_calls().filter(is_inbound=True).last()
        if is_google_ads_call_asset(phone_call=phone_call):
            return

        # Report Conversion
        data = self._create_data_dict(LeadStatusChoices.LEAD_CREATED)

        conversion_service.send_conversion(data=data)
        
    def _on_invoice_sent(self, context: LeadTransitionContext):
        pass

    def _on_event_booked(self, context: LeadTransitionContext):
        data = self._create_data_dict(LeadStatusChoices.EVENT_BOOKED, event=context.event)
        conversion_service.send_conversion(data=data)

    def _on_archived(self, context: LeadTransitionContext):
        pass

    def _create_data_dict(self, event_name=None, event=None):
        data = {
            'event_name': event_name,
            'ip_address': self.lead.lead_marketing.ip,
            'user_agent': self.lead.lead_marketing.user_agent,
            'instant_form_lead_id': self.lead.lead_marketing.instant_form_lead_id,
            'event_time': int(timezone.now().timestamp()),
            'phone_number': self.lead.phone_number,
            'lead_id': self.lead.pk,
            'external_id': str(self.lead.lead_marketing.external_id)
        }

        if event_name == LeadStatusChoices.EVENT_BOOKED and event:
            data.update({
                'event_id': event.pk,
                'value': event.amount,
            })

        for metadata in self.lead.lead_marketing.metadata.all():
            if metadata.key == '_fbc':
                data['fbc'] = metadata.value
            elif metadata.key == '_fbp':
                data['fbp'] = metadata.value
            elif metadata.key == '_ga':
                data['ga'] = metadata.value
            elif metadata.key == 'gclid':
                data['gclid'] = metadata.value
            elif metadata.key == 'gbraid':
                data['gbraid'] = metadata.value
            elif metadata.key == 'wbraid':
                data['wbraid'] = metadata.value
            elif metadata.key == '_gcl_aw':
                if 'gclid' not in data:
                    cookie_click_id = parse_google_ads_cookie(metadata.value)
                    if cookie_click_id:
                        data['gclid'] = cookie_click_id
            else:
                data[metadata.key] = metadata.value
            
        return data
    
    @transaction.atomic
    def archive(self, source: str = "system", user: Optional[User] = None):
        if self.current_status == LeadStatusChoices.ARCHIVED:
            return

        context = LeadTransitionContext(user=user, source=source)
        self.transition_to(LeadStatusChoices.ARCHIVED, context=context)