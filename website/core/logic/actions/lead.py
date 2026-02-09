from django.db import models

from core.models import Lead, Message
from core.utils import format_text_message, get_most_frequent_communication_user
from core.services.messaging import messaging_service
from core.enums import EngagementAction, FollowUpVariant

class LeadAction:

    def __init__(self, lead: Lead):
        self.lead = lead

    def _send_text(self, from_number, to_number, text):
        message = Message(
            text=format_text_message(text),
            text_from=from_number,
            text_to=to_number,
            is_inbound=False,
            status="sent",
            is_read=True,
        )
        resp = messaging_service.send_text_message(message=message)
        message.external_id = resp.sid
        message.status = resp.status
        message.save()

    def send_automated_message(self, action: EngagementAction):
        if action == EngagementAction.SEND_INITIAL_CONTACT:
            self._send_initial_contact()

        elif action == EngagementAction.SEND_FOLLOW_UP_1:
            self._send_follow_up(variant="first")

        elif action == EngagementAction.SEND_FOLLOW_UP_2:
            self._send_follow_up(variant="second")
    
    def _send_initial_contact(self):
        user = get_most_frequent_communication_user(messages=self.lead.messages())

        text = "\n".join([
            f"Hi {self.lead.full_name}, thanks for reaching out!",
            f"I’ll be helping you with your request.",
        ])

        self._send_text(
            from_number=user.forward_phone_number,
            to_number=self.lead.phone_number,
            text=text,
        )
    
    def _build_follow_up_text(self, variant: str) -> str:
        if variant == FollowUpVariant.FIRST:
            return "\n".join([
                f"Hey {self.lead.full_name}, just following up!",
                f"Let me know if you have any questions.",
            ])

        if variant == FollowUpVariant.SECOND:
            return "\n".join([
                f"Hi {self.lead.full_name}, one last follow up from us.",
                f"We’re here whenever you’re ready.",
            ])

        raise ValueError(f"Unknown follow-up variant: {variant}")

    def _send_follow_up(self, variant: str):
        user = get_most_frequent_communication_user(messages=self.lead.messages())

        text_content = self._build_follow_up_text(lead=self.lead, variant=variant)

        message = Message(
            text=format_text_message(text_content),
            text_from=user.forward_phone_number,
            text_to=self.lead.phone_number,
            is_inbound=False,
            status='sent',
            is_read=True,
        )

        resp = messaging_service.send_text_message(message=message)
        message.external_id = resp.sid
        message.status = resp.status
        message.save()