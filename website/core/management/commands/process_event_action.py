from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.models import Event, EventStatusChoices, EventTaskLog
from core.managers.event import EventManager


class Command(BaseCommand):
    help = "Runs scheduled event actions such as reminders or notifications."

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            required=True,
            help="Action to perform (e.g. send_onboarding_reminder)"
        )

    def handle(self, *args, **options):
        action = options['action']

        action_to_status = {
            "send_onboarding_reminder": EventStatusChoices.ONBOARDING,
            "send_finalize_event_details_reminder": EventStatusChoices.AWAITING_CLIENT_CONFIRMATION,
            "send_event_confirmation_notification": EventStatusChoices.CONFIRMED,
            "mark_event_completed": EventStatusChoices.IN_PROGRESS,
            "send_review_request": EventStatusChoices.SERVICE_COMPLETED,
        }

        target_status = action_to_status.get(action)
        if not target_status:
            raise CommandError(f"❌ No status mapping found for action '{action}'")

        events = Event.objects.select_related("lead", "event_status").filter(event_status__status=target_status)

        if not events.exists():
            return

        for event in events:
            manager = EventManager(event)
            manager.process_background_action(action, triggered_by="cron")