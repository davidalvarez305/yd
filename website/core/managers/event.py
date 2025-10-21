from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from website import settings

from core.models import Event, EventStatus, EventStatusHistory, EventStatusChoices, LeadStatusEnum, Message, User
from core.email import email_service
from core.messaging import messaging_service
from crm.utils import generate_event_pdf
from core.logger import logger

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
    
    def process_background_action(self, action: str, **kwargs):
        """
        Handle background or scheduled event actions (triggered via management command).
        Example: process_action("send_onboarding_reminder")
        """
        actions = {
            "send_onboarding_reminder": self._send_onboarding_reminder,
            "send_finalize_event_details_reminder": self._send_finalize_event_details_reminder,
            "send_event_confirmation_notification": self._send_event_confirmation_notification,
            "mark_service_completed": self.mark_service_completed,
        }

        if action not in actions:
            logger.error(f"Unknown action '{action}' for event {self.event.pk}")
            raise ValidationError(f"Unknown action '{action}'")

        logger.info(f"Executing action '{action}' for event {self.event.pk}")
        return actions[action](**kwargs)

    def book(self):
        return self.transition_to(EventStatusChoices.BOOKED)

    def confirm(self):
        return self.transition_to(EventStatusChoices.CONFIRMED)

    def start_service(self):
        return self.transition_to(EventStatusChoices.IN_PROGRESS)

    def mark_service_completed(self):
        return self.transition_to(EventStatusChoices.SERVICE_COMPLETED)

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
    
    def _send_event_confirmation_notification(self):
        document = generate_event_pdf(event=self.event)
        document_url = reverse('event_external_document_detail', kwargs={ 'external_id': self.event.external_id, 'document_name': document.document.name.split('/')[-1] })

        # Client Text
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