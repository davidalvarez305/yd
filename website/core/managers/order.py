from django.db import transaction
from datetime import datetime, time, timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from website import settings

from core.email import email_service
from core.models import Lead, LeadStatusEnum, Message, OrderStatus, OrderStatusChangeHistory, OrderStatusChoices, PhoneCallTranscription, User
from core.messaging import messaging_service
from core.ai import ai_agent

class InvalidOrderTransitionError(ValidationError):
    """Raised when an invalid order state transition is attempted."""
    pass

class OrderManager:

    TRANSITIONS = {
        OrderStatusChoices.ORDER_PLACED: [
            OrderStatusChoices.AWAITING_PREPARATION,
        ],
        OrderStatusChoices.AWAITING_PREPARATION: [
            OrderStatusChoices.READY_FOR_DISPATCH,
        ],
        OrderStatusChoices.READY_FOR_DISPATCH: [
            OrderStatusChoices.DISPATCHED,
        ],
        OrderStatusChoices.DISPATCHED: [
            OrderStatusChoices.DELIVERED,
        ],
        OrderStatusChoices.DELIVERED: [
            OrderStatusChoices.PENDING_PICK_UP,
        ],
        OrderStatusChoices.PENDING_PICK_UP: [
            OrderStatusChoices.PICKED_UP,
        ],
        OrderStatusChoices.PICKED_UP: [
            OrderStatusChoices.READY_FOR_STORAGE,
        ],
        OrderStatusChoices.READY_FOR_STORAGE: [
            OrderStatusChoices.FINALIZED,
        ],
        OrderStatusChoices.FINALIZED: [],
    }

    def __init__(self, order, user=None):
        self.order = order
        self.user = user

    @property
    def current_status(self):
        return self.order.status.status if self.order.status else None

    def can_transition_to(self, new_status: str) -> bool:
        if not self.current_status:
            return True
        return new_status in self.TRANSITIONS.get(self.current_status, [])

    @transaction.atomic
    def transition_to(self, new_status: str, user: User | None, lead: Lead | None):
        if self.current_status and not self.can_transition_to(new_status):
            raise InvalidOrderTransitionError(
                f"Cannot transition order {self.order.code} "
                f"from '{self.current_status}' to '{new_status}'"
            )

        status = OrderStatus.objects.get(status=new_status)

        self.order.status = status
        self.order.save(update_fields=['status'])

        OrderStatusChangeHistory.objects.create(
            order=self.order,
            status=status,
            user=user,
            lead=lead,
        )

        self._run_hooks(new_status)
    
    def place_order(self):
        return self.transition_to(OrderStatusChoices.ORDER_PLACED)
    
    def mark_ready_for_dispatch(self):
        return self.transition_to(OrderStatusChoices.READY_FOR_DISPATCH)

    def dispatch(self):
        return self.transition_to(OrderStatusChoices.DISPATCHED)

    def mark_delivered(self):
        return self.transition_to(OrderStatusChoices.DELIVERED)

    def mark_pending_pickup(self):
        return self.transition_to(OrderStatusChoices.PENDING_PICK_UP)

    def pickup_completed(self):
        return self.transition_to(OrderStatusChoices.PICKED_UP)

    def store_items(self):
        return self.transition_to(OrderStatusChoices.READY_FOR_STORAGE)

    def finalize(self):
        return self.transition_to(OrderStatusChoices.FINALIZED)

    def _run_hooks(self, new_status):
        match new_status:
            case OrderStatusChoices.ORDER_PLACED:
                self._on_place_order()
            case OrderStatusChoices.AWAITING_PREPARATION:
                self._on_awaiting_preparation()
            case OrderStatusChoices.READY_FOR_DISPATCH:
                self._on_ready_for_dispatch()
            case OrderStatusChoices.DISPATCHED:
                self._on_dispatched()
            case OrderStatusChoices.DELIVERED:
                self._on_delivered()
            case OrderStatusChoices.PICKED_UP:
                self._on_picked_up()
            case OrderStatusChoices.FINALIZED:
                self._on_finalized()

    def _on_place_order(self):

        # Reserve items on order & log inventory event
        for item in self.order.items.all():
            item.reserve_item(
                quantity=item.units,
                start_date=data.get('start_date'),
                end_date=data.get('end_date'),
                order=self,
            )

        # Report conversion event
        self.order.lead.change_lead_status(LeadStatusEnum.EVENT_BOOKED, event=self.order)
        
        # Alert client
        self._send_order_placed_confirmation_email()
        
        # Transition to next step in workflow
        self.transition_to(OrderStatusChoices.AWAITING_PREPARATION)

    def _send_order_placed_confirmation_email(self):
        html = f"""
            <html>
            <body>
                <p>Email!</p>
            </body>
            </html>
        """
        
        email_service.send_html_email(
            to=settings.COMPANY_EMAIL,
            subject=f"{self.event.lead.full_name} Order Placed",
            html=html
        )
    
    def _on_awaiting_preparation(self):
        return

    def _on_ready_for_dispatch(self):
        # e.g. assign driver, notify warehouse
        pass

    def _on_dispatched(self):
        # e.g. mark inventory IN_TRUCK
        pass

    def _on_delivered(self):
        # e.g. mark inventory ON_SITE
        pass

    def _on_picked_up(self):
        # e.g. create ItemStateChangeHistory(Returned)
        pass

    def _on_finalized(self):
        # e.g. close order, release holds
        pass

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