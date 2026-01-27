import json
from django.db import transaction
from django.utils import timezone
from core.models import LandingPage, LandingPageConversion, LeadMarketingMetadata, LeadStatus, LeadStatusChoices, Lead, LeadStatusHistory, SessionMapping, TrackingPhoneCall, TrackingPhoneCallMetadata, User
from dataclasses import dataclass
from typing import Optional

@dataclass
class LeadTransitionContext:
    user: Optional[User] = None
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
            LeadStatusChoices.RE_ENGAGED,
            LeadStatusChoices.ARCHIVED,
        },
        LeadStatusChoices.RE_ENGAGED: {
            LeadStatusChoices.INVOICE_SENT,
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
    def transition_to(self, status: str, context: LeadTransitionContext | None = None) -> LeadStatusHistory:
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

        self.lead.lead_status = lead_status
        self.lead.save(update_fields=["lead_status"])

        history = LeadStatusHistory.objects.create(
            lead=self.lead,
            lead_status=lead_status,
            date_changed=timezone.now(),
        )

        self._run_hooks(status, context)

        return history

    def _run_hooks(self, status: LeadStatusChoices, context: LeadTransitionContext):
        match status:
            case LeadStatusChoices.LEAD_CREATED:
                self._on_lead_created(context)
            case LeadStatusChoices.INVOICE_SENT:
                self._on_invoice_sent(context)
            case LeadStatusChoices.EVENT_BOOKED:
                self._on_event_booked(context)
            case LeadStatusChoices.RE_ENGAGED:
                self._on_re_engaged(context)
            case LeadStatusChoices.ARCHIVED:
                self._on_archived(context)

    def _on_lead_created(self, context: LeadTransitionContext):
        
        # Report Lead to Google
        last_inbound_call = TrackingPhoneCall.objects.filter(call_from=self.lead.phone_number).order_by('-date_created').first()

        if last_inbound_call:
            phone_call_metadata = TrackingPhoneCallMetadata.objects.filter(tracking_phone_call=last_inbound_call)

            metadata = phone_call_metadata.filter(key="custom").first()

            if metadata:
                try:
                    params = json.loads(metadata.value) or {}

                    lp = params.get("calltrk_landing")
                    if lp:
                        params |= generate_params_dict_from_url(lp)

                    external_id = params.get(settings.TRACKING_COOKIE_NAME)
                    if external_id:
                        session_mapping = SessionMapping.objects.filter(external_id=external_id).first()
                        if session_mapping:
                            session = get_session_data(session_key=session_mapping.session_key)

                            self.lead.lead_marketing.ip = session.get('ip')
                            self.lead.lead_marketing.user_agent = session.get('user_agent')
                            self.lead.lead_marketing.external_id = external_id
                            self.lead.lead_marketing.ad = create_ad_from_params(params=params, cookies=params)
                            self.lead.lead_marketing.save()
                            self.lead.lead_marketing.assign_visits()

                            landing_page_id = session.get('landing_page_id')
                            if landing_page_id:
                                landing_page = LandingPage.objects.filter(pk=landing_page_id).first()
                                if landing_page:
                                    conversion = LandingPageConversion(
                                        lead=self.lead,
                                        landing_page=landing_page,
                                        conversion_type=LandingPageConversion.PHONE_CALL
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

            # Do not report conversions for call asset calls
            if is_google_ads_call_asset(phone_call=last_inbound_call):
                return

        # Now that the marketing data has been assigned, generate the data dict and send conversion
        # Get the lead with the updated marketing data
        lead = Lead.objects.get(pk=self.lead.pk)
        data = create_data_dict(lead, event_name, event)

        conversion_service.send_conversion(data=data)
        
        # Notify Users

    def _on_invoice_sent(self, context: LeadTransitionContext):
        self._schedule_second_follow_up()

    def _on_event_booked(self, context: LeadTransitionContext):
        self._close_open_tasks()

    def _on_archived(self, context: LeadTransitionContext):
        self._cancel_pending_tasks()