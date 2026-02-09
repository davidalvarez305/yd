from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from core.models import (
    Lead,
    LeadEngagementState,
    LeadEngagementHistory,
    LeadEngagementStateChoices,
)

ENGAGEMENT_TIMEOUTS = {
    LeadEngagementStateChoices.FIRST_CONTACT: timedelta(hours=24),
    LeadEngagementStateChoices.FOLLOW_UP_1: timedelta(hours=48),
    LeadEngagementStateChoices.FOLLOW_UP_2: timedelta(hours=72),
}

MAX_FOLLOW_UPS = 2
MAX_RETRIES = 3

class InvalidEngagementTransition(ValidationError):
    pass

class LeadEngagementManager:
    TRANSITIONS = {
        LeadEngagementStateChoices.IDLE: {
            LeadEngagementStateChoices.FIRST_CONTACT,
        },
        LeadEngagementStateChoices.FIRST_CONTACT: {
            LeadEngagementStateChoices.FOLLOW_UP_1,
            LeadEngagementStateChoices.RESPONDED,
        },
        LeadEngagementStateChoices.FOLLOW_UP_1: {
            LeadEngagementStateChoices.FOLLOW_UP_2,
            LeadEngagementStateChoices.RESPONDED,
        },
        LeadEngagementStateChoices.FOLLOW_UP_2: {
            LeadEngagementStateChoices.RESPONDED,
            LeadEngagementStateChoices.NO_RESPONSE,
        },
        LeadEngagementStateChoices.RESPONDED: {
            LeadEngagementStateChoices.FIRST_CONTACT,
        },
        LeadEngagementStateChoices.NO_RESPONSE: set(),
    }

    TERMINAL_STATES = {
        LeadEngagementStateChoices.NO_RESPONSE,
    }

    def __init__(self, lead: Lead):
        self.lead = lead

    def _get_or_create_state(self) -> LeadEngagementState:
        state, _ = LeadEngagementState.objects.get_or_create(
            lead=self.lead,
            defaults={"state": LeadEngagementStateChoices.IDLE},
        )
        return state

    @property
    def engagement(self) -> LeadEngagementState:
        return self._get_or_create_state()

    @property
    def current_state(self) -> LeadEngagementStateChoices:
        return LeadEngagementStateChoices(self.engagement.state)

    def can_transition_to(self, new_state: LeadEngagementStateChoices) -> bool:
        return new_state in self.TRANSITIONS.get(self.current_state, set())

    def _validate_transition(self, new_state: LeadEngagementStateChoices):
        if self.current_state in self.TERMINAL_STATES:
            raise InvalidEngagementTransition(
                f"Engagement already terminal ({self.current_state})"
            )

        if not self.can_transition_to(new_state):
            raise InvalidEngagementTransition(
                f"Cannot transition from {self.current_state} → {new_state}"
            )

    def _record_history(self, from_state, to_state, triggered_by):
        LeadEngagementHistory.objects.create(
            lead=self.lead,
            from_state=from_state,
            to_state=to_state,
            follow_up_attempts=self.engagement.follow_up_attempts,
            retry_cycles=self.engagement.retry_cycles,
            triggered_by=triggered_by,
        )

    def _transition_to(self, new_state, triggered_by):
        if self.current_state == new_state:
            return

        self._validate_transition(new_state)

        self._record_history(
            from_state=self.current_state,
            to_state=new_state,
            triggered_by=triggered_by,
        )

        self.engagement.state = new_state
        self.engagement.date_updated = timezone.now()
    
    @transaction.atomic
    def start_contact(self, triggered_by="system"):
        if self.current_state not in (
            LeadEngagementStateChoices.IDLE,
            LeadEngagementStateChoices.RESPONDED,
        ):
            raise InvalidEngagementTransition(
                f"Cannot start contact from {self.current_state}"
            )

        self.engagement.last_contacted_at = timezone.now()
        self.engagement.follow_up_attempts = 0
        self._transition_to(LeadEngagementStateChoices.FIRST_CONTACT, triggered_by=triggered_by)
        self.engagement.save()
    
    @transaction.atomic
    def send_follow_up(self, triggered_by="system"):
        if self.current_state not in (
            LeadEngagementStateChoices.FIRST_CONTACT,
            LeadEngagementStateChoices.FOLLOW_UP_1,
        ):
            raise InvalidEngagementTransition(
                f"Cannot follow up from {self.current_state}"
            )

        if self.engagement.follow_up_attempts >= MAX_FOLLOW_UPS:
            raise InvalidEngagementTransition("Max follow-ups reached")

        self.engagement.follow_up_attempts += 1
        self.engagement.last_contacted_at = timezone.now()

        next_state = (
            LeadEngagementStateChoices.FOLLOW_UP_1
            if self.engagement.follow_up_attempts == 1
            else LeadEngagementStateChoices.FOLLOW_UP_2
        )

        self._transition_to(next_state, triggered_by=triggered_by)
        self.engagement.save()
    
    @transaction.atomic
    def record_response(self, source="unknown"):
        if self.current_state == LeadEngagementStateChoices.RESPONDED:
            return

        self.engagement.last_responded_at = timezone.now()
        self.engagement.follow_up_attempts = 0
        self.engagement.retry_cycles = 0
        self._transition_to(LeadEngagementStateChoices.RESPONDED, triggered_by=source)
        self.engagement.save()
    
    @transaction.atomic
    def mark_no_response(self, triggered_by="system"):
        if self.current_state != LeadEngagementStateChoices.FOLLOW_UP_2:
            raise InvalidEngagementTransition(
                "No-response only valid after second follow-up"
            )

        self.engagement.retry_cycles += 1
        self.engagement.follow_up_attempts = 0

        if self.engagement.retry_cycles >= MAX_RETRIES:
            self._transition_to(LeadEngagementStateChoices.NO_RESPONSE, triggered_by=triggered_by)
            self.engagement.save()
            self.lead.manager.archive(source="engagement_timeout")
            return

        self.engagement.last_contacted_at = timezone.now()
        self._transition_to(LeadEngagementStateChoices.FIRST_CONTACT, triggered_by=triggered_by)
        self.engagement.save()
    
    def is_paused(self) -> bool:
        paused_until = self.engagement.paused_until
        return paused_until is None or paused_until > timezone.now()
    
    def evaluate_time_based_transitions(self):
        now = timezone.now()
        state = self.current_state

        if self.is_paused(now):
            return

        if state in self.TERMINAL_STATES:
            return

        timeout = ENGAGEMENT_TIMEOUTS.get(state)
        if not timeout:
            return

        last_contact = self.engagement.last_contacted_at
        if not last_contact:
            return

        if now - last_contact < timeout:
            return

        if state in (
            LeadEngagementStateChoices.FIRST_CONTACT,
            LeadEngagementStateChoices.FOLLOW_UP_1,
        ):
            self.send_follow_up(triggered_by="timeout")

        elif state == LeadEngagementStateChoices.FOLLOW_UP_2:
            self.mark_no_response(triggered_by="timeout")
    
    @transaction.atomic
    def pause_on_inbound(self, source="inbound"):
        self.engagement.paused_until = None
        self.engagement.save(update_fields=["paused_until"])
        self.record_response(source=source)