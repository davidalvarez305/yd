from django.db import transaction

from core.models import Lead, LeadEngagementStateChoices, Message
from core.services.messaging import messaging_service
from core.enums import EngagementAction, FollowUpVariant
from core.utils import format_text_message, get_most_frequent_communication_user

class LeadEngagementProcessor:

    def run(self, *, limit=500):
        leads = self._get_candidates(limit=limit)

        for lead in leads:
            self._process_lead(lead)

    def _get_candidates(self, limit):
        return (
            Lead.objects
            .select_related("engagement")
            .filter(
                engagement__state__in=[
                    LeadEngagementStateChoices.FIRST_CONTACT,
                    LeadEngagementStateChoices.FOLLOW_UP_1,
                    LeadEngagementStateChoices.FOLLOW_UP_2,
                ],
            )
            .order_by("engagement__last_contacted_at")[:limit]
        )

    @transaction.atomic
    def _process_lead(self, lead: Lead):
        action, variant = lead.engagement_manager.evaluate_time_based_transitions()

        if action == EngagementAction.NONE:
            return

        if action == EngagementAction.SEND_FOLLOW_UP:
            self.lead.actions.send_follow_up(variant=variant)