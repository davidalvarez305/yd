from datetime import datetime, time, timedelta
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from website import settings

from core.models import Event, EventStatus, EventStatusHistory, EventStatusChoices, EventTaskLog, LeadStatusEnum, Message, PhoneCallTranscription, User
from core.email import email_service
from core.messaging import messaging_service
from crm.utils import generate_event_pdf
from core.ai import ai_agent
class InvalidTransitionError(ValidationError):

    """Raised when an invalid event state transition is attempted."""
    pass

class EventManager:

    TRANSITIONS = {
        EventStatusChoices.BOOKED: [
            EventStatusChoices.ONBOARDING,
            EventStatusChoices.CANCELLED if hasattr(EventStatusChoices, "CANCELLED") else None,
        ],
        EventStatusChoices.ONBOARDING: [
            EventStatusChoices.AWAITING_CLIENT_CONFIRMATION,
        ],
        EventStatusChoices.AWAITING_CLIENT_CONFIRMATION: [
            EventStatusChoices.CONFIRMED,
            EventStatusChoices.CANCELLED if hasattr(EventStatusChoices, "CANCELLED") else None,
        ],
        EventStatusChoices.CONFIRMED: [
            EventStatusChoices.AWAITING_STAFF_ASSIGNMENT,
        ],
        EventStatusChoices.AWAITING_STAFF_ASSIGNMENT: [
            EventStatusChoices.ONBOARDING_COMPLETED,
        ],
        EventStatusChoices.ONBOARDING_COMPLETED: [
            EventStatusChoices.IN_PROGRESS,
        ],
        EventStatusChoices.IN_PROGRESS: [
            EventStatusChoices.EXTENDED,
            EventStatusChoices.SERVICE_COMPLETED,
        ],
        EventStatusChoices.EXTENDED: [
            EventStatusChoices.SERVICE_COMPLETED,
        ],
        EventStatusChoices.SERVICE_COMPLETED: [],
    }

    def __init__(self, event: Event, user=None):
        self.event = event
        self.user = user

    def can_transition_to(self, new_status: str) -> bool:
        current_status = self.event.event_status.status if self.event.event_status else None
        allowed = self.TRANSITIONS.get(current_status, [])
        return new_status in allowed

    def transition_to(self, new_status: str):
        current_status = self.event.event_status.status if self.event.event_status else None

        if current_status and not self.can_transition_to(new_status):
            raise InvalidTransitionError(
                f"Cannot transition from '{current_status}' to '{new_status}'"
            )

        event_status = EventStatus.objects.get(status=new_status)

        self.event.event_status = event_status
        self.event.save(update_fields=['event_status'])

        EventStatusHistory.objects.create(
            event=self.event,
            event_status=event_status,
            user=self.user,
        )

        self._run_hooks(new_status)
    
    def process_background_action(self, action: str, triggered_by="cron", **kwargs):
        """Process a background action with automatic logging and error handling."""

        actions = {
            "send_onboarding_reminder": self._send_onboarding_reminder,
            "send_event_confirmation_notification": self._send_event_confirmation_notification,
            "mark_service_completed": self._mark_service_completed,
            "send_review_request": self._send_review_request,
            "send_client_confirmation_reminder": self._send_client_confirmation_reminder,
        }

        if action not in actions:
            raise ValidationError(f"Unknown action '{action}'")

        log = EventTaskLog.objects.create(
            event=self.event,
            action=action,
            triggered_by=triggered_by,
            started_at=timezone.now(),
        )

        try:
            actions[action](**kwargs)

            log.mark_completed(success=True)
        except Exception as e:
            log.mark_completed(success=False, message=str(e))

    def book(self):
        return self.transition_to(EventStatusChoices.BOOKED)

    def confirm(self):
        return self.transition_to(EventStatusChoices.CONFIRMED)

    def start_service(self):
        return self.transition_to(EventStatusChoices.IN_PROGRESS)

    def _run_hooks(self, new_status):
        match new_status:
            case EventStatusChoices.BOOKED:
                self._on_book()
            case EventStatusChoices.CONFIRMED:
                self._on_confirmed()
            case EventStatusChoices.IN_PROGRESS:
                self._on_in_progress()
            case EventStatusChoices.SERVICE_COMPLETED:
                self._on_completed()

    def _on_book(self):
        self.event.lead.change_lead_status(LeadStatusEnum.EVENT_BOOKED, event=self.event)
        self._send_lead_event_booking_notification()
        self._send_onboarding_reminder()
        self.transition_to(EventStatusChoices.ONBOARDING)

    def _on_confirmed(self):
        self._send_event_confirmation_notification()

    def _on_in_progress(self):
        print(f"Event {self.event.event_id} started at {timezone.now()}.")

    def _on_completed(self):
        print(f"Event {self.event.event_id} completed.")
    
    def _send_onboarding_reminder(self):
        if not self.event.event_status or self.event.event_status.status != EventStatusChoices.ONBOARDING:
            return

        now = timezone.now()

        time_until_event = self.event.quote.event_date - now
        send_interval = timedelta(hours=24 if time_until_event <= timedelta(days=14) else 48)

        last_log = (
            EventTaskLog.objects.filter(
                event=self.event,
                action="send_onboarding_reminder",
                status="success"
            )
            .order_by("-executed_at")
            .first()
        )

        if last_log and now - last_log.executed_at < send_interval:
            return

        event_details = settings.ROOT_DOMAIN + reverse("event_detail", kwargs={ 'pk': self.event.pk })
        html = f"""
            <html>
            <body>
                <p><a href="{event_details}">View Event Details</a></p>
            </body>
            </html>
        """
        
        email_service.send_html_email(
            to=settings.COMPANY_EMAIL,
            subject=f"Finalize {self.event.lead.full_name}'s Event Details",
            html=html
        )
    
    def _send_client_confirmation_reminder(self):
        if not self.event.event_status or self.event.event_status.status != EventStatusChoices.AWAITING_CLIENT_CONFIRMATION:
            return

        now = timezone.now()

        time_until_event = self.event.quote.event_date - now
        send_interval = timedelta(hours=24 if time_until_event <= timedelta(days=7) else 96)

        last_log = (
            EventTaskLog.objects.filter(
                event=self.event,
                action="send_client_confirmation_reminder",
                status="success"
            )
            .order_by("-executed_at")
            .first()
        )

        if last_log and now - last_log.executed_at < send_interval:
            return

        lead = self.event.lead
        event_date = self.event.quote.event_date.strftime("%b %d, %Y")
        event_details = settings.ROOT_DOMAIN + reverse("event_detail", kwargs={"pk": self.event.pk})

        text = "\n".join([
            f"Hi {lead.full_name},",
            f"This is a friendly reminder to confirm your event details for {event_date}.",
            f"You can review and confirm everything here:",
            f"{event_details}",
        ])
        message = Message(
            text=text,
            text_from=settings.COMPANY_PHONE_NUMBER,
            text_to=lead.phone_number,
            is_inbound=False,
            status='sent',
            is_read=True,
        )
        response = messaging_service.send_text_message(message)
        message.external_id = response.sid
        message.save()

    def _send_event_confirmation_notification(self):
        document = generate_event_pdf(event=self.event)
        document_url = reverse('event_external_document_detail', kwargs={ 'external_id': self.event.external_id, 'document_name': document.document.name.split('/')[-1] })

        text = "\n".join([
            f"EVENT DETAILS CONFIRMED!",
            f"Hi {self.event.lead.full_name},",
            f"Thank you for confirming all the details about your event. Here's the trail of everything that's happened so far, for your records:",
            f"LINK: {document_url}"
        ])
        message = Message(
            text=text,
            text_from=settings.COMPANY_PHONE_NUMBER,
            text_to=self.event.lead.phone_number,
            is_inbound=False,
            status='sent',
            is_read=True,
        )
        response = messaging_service.send_text_message(message)
        message.external_id = response.sid
        message.save()

        # Internal E-mail
        html = f"""
            <html>
            <body>
                <p><a href="{document_url}">Get Event PDF</a></p>
            </body>
            </html>
        """
        
        email_service.send_html_email(
            to=settings.COMPANY_EMAIL,
            subject=f"{self.event.lead.full_name} Has Confirmed Event's Details!",
            html=html
        )
    
    def _send_lead_event_booking_notification(self):
        users_to_notify = [u.forward_phone_number for u in User.objects.filter(is_superuser=True)]
        users_to_notify.append(self.event.lead.phone_number)

        for phone_number in users_to_notify:
            text = "\n".join([
                f"EVENT BOOKED:",
                f"Date: {self.event.quote.event_date.strftime('%b %d, %Y')}",
                f"Full Name: {self.event.lead.full_name}",
            ])
            message = Message(
                text=text,
                text_from=settings.COMPANY_PHONE_NUMBER,
                text_to=phone_number,
                is_inbound=False,
                status='sent',
                is_read=True,
            )
            response = messaging_service.send_text_message(message)
            message.external_id = response.sid
            message.save()

    def _mark_service_completed(self):
        if timezone.now() > self.event.end_time:
            return self.transition_to(EventStatusChoices.SERVICE_COMPLETED)

    def _send_review_request(self):
        review_link = "https://g.page/r/CQaxh0zJ4KNwEAE/review"

        if not self.event.event_status or self.event.event_status.status != EventStatusChoices.SERVICE_COMPLETED:
            return

        if EventTaskLog.objects.filter(event=self.event, action="send_review_request", status="success").exists():
            return

        completed_at = self.event.statuses.filter(event_status__status=EventStatusChoices.SERVICE_COMPLETED).order_by("-date_created").values_list("date_created", flat=True).first()

        if not completed_at:
            return

        next_day_noon = timezone.make_aware(datetime.combine((completed_at + timedelta(days=1)).date(), time(12, 0)))

        if timezone.now() < next_day_noon:
            return

        lead = self.event.lead
        event_date = self.event.quote.event_date.strftime('%b %d, %Y')

        first_transcription = (
            PhoneCallTranscription.objects
            .filter(phone_call__in=lead.phone_calls())
            .order_by('date_created')
            .values_list('text', flat=True)
            .first()
        )

        if first_transcription:
            language_context = first_transcription[:1000]
        else:
            recent_messages = (
                Message.objects
                .filter(text_to=lead.phone_number)
                .order_by('-date_created')[:10]
                .values_list('text', flat=True)
            )
            language_context = "\n".join(reversed(recent_messages))[:1000]

        prompt = f"""
    You are a friendly assistant for a bartending service.

    The client may speak English or Spanish. Detect the language they use from the text below,
    and generate the message in that same language.

    Context for language detection (client communication sample):
    {language_context}

    Now, generate a short, friendly review request message for this client:

    - Client Name: {lead.full_name}
    - Event Date: {event_date}
    - Review Link: {review_link}

    Make it natural, positive, and no longer than 4 sentences.
    Include the review link organically in the message.
    """

        ai_text = ai_agent.generate_response(prompt=prompt, stream=True)

        if not ai_text.strip():
            ai_text = "\n".join([
                f"HOW DID IT GO? 🍸",
                f"Date: {event_date}",
                f"Hi {lead.full_name}, we hope you had an amazing time at your event!",
                "We’d really appreciate it if you could take a minute to share your experience with us:",
                review_link,
                "Your feedback helps us improve and means a lot to our team. Thank you!"
            ])

        message = Message(
            text=ai_text,
            text_from=settings.COMPANY_PHONE_NUMBER,
            text_to=lead.phone_number,
            is_inbound=False,
            status='sent',
            is_read=True,
        )

        response = messaging_service.send_text_message(message)
        message.external_id = response.sid
        message.save()

        return message