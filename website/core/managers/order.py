from django.db import transaction
from datetime import datetime, time, timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.template.loader import render_to_string
from website import settings

from core.email import email_service
from core.models import AddedOrRemoveActionChoices, Item, Lead, LeadStatusEnum, Message, Order, OrderItem, OrderItemChangeHistory, OrderService, OrderServiceChangeHistory, OrderStatus, OrderStatusChangeHistory, OrderStatusChoices, PhoneCallTranscription, Service, User
from core.messaging import messaging_service
from core.ai import ai_agent

class InvalidOrderTransitionError(ValidationError):
    """Raised when an invalid order state transition is attempted."""
    pass

class OrderManager:

    BASE_TRANSITIONS = {
        OrderStatusChoices.ORDER_PLACED: [
            OrderStatusChoices.AWAITING_PREPARATION,
        ],
        OrderStatusChoices.AWAITING_PREPARATION: [
            OrderStatusChoices.READY_FOR_DISPATCH,
        ],
        OrderStatusChoices.READY_FOR_DISPATCH: [
            OrderStatusChoices.DISPATCHED,
        ]
    }

    CANCELLABLE_STATUSES = {
        OrderStatusChoices.ORDER_PLACED,
        OrderStatusChoices.AWAITING_PREPARATION,
        OrderStatusChoices.READY_FOR_DISPATCH,
        OrderStatusChoices.DISPATCHED,
    }

    UPDATABLE_STATUSES = {
        OrderStatusChoices.ORDER_PLACED,
        OrderStatusChoices.AWAITING_PREPARATION,
    }

    def __init__(self, order):
        self.order = order

    @property
    def current_status(self):
        return self.order.status.status if self.order.status else None
    
    def allowed_transitions(self):
        status = self.current_status
        if not status:
            return []

        transitions = list(self.BASE_TRANSITIONS.get(status, []))

        if self.order.has_delivery:
            delivery_flow = {
                OrderStatusChoices.DISPATCHED: [
                    OrderStatusChoices.DELIVERED
                ],
                OrderStatusChoices.DELIVERED: [
                    OrderStatusChoices.PENDING_PICK_UP
                ],
                OrderStatusChoices.PENDING_PICK_UP: [
                    OrderStatusChoices.PICKED_UP
                ],
                OrderStatusChoices.PICKED_UP: [
                    OrderStatusChoices.FINALIZED
                ],
            }
            transitions.extend(delivery_flow.get(status, []))
        else:
            pickup_flow = {
                OrderStatusChoices.DISPATCHED: [
                    OrderStatusChoices.CUSTOMER_PICKED_UP
                ],
                OrderStatusChoices.CUSTOMER_PICKED_UP: [
                    OrderStatusChoices.CUSTOMER_RETURNED
                ],
                OrderStatusChoices.CUSTOMER_RETURNED: [
                    OrderStatusChoices.FINALIZED
                ],
            }
            transitions.extend(pickup_flow.get(status, []))

        return transitions

    def can_transition_to(self, new_status: str) -> bool:
        if not self.current_status:
            return True
        return new_status in self.allowed_transitions()

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
    
    @transaction.atomic
    def _force_transition(self, new_status: str, user: User | None, lead: Lead | None):
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
    
    @transaction.atomic
    def update_order_items(self, updated_items: list[dict]):
        if self.current_status not in self.UPDATABLE_STATUSES:
            raise InvalidOrderTransitionError(
                "Order items cannot be updated at this stage"
            )

        self._sync_order_items(updated_items)
    
    @transaction.atomic
    def add_item(self, item_id: int, units: int):
        self._add_item(item_id, units)

    @transaction.atomic
    def remove_item(self, order_item: OrderItem):
        self._remove_item(order_item)

    @transaction.atomic
    def add_service(self, service_id: int, units: int):
        self._add_service(service_id, units)

    @transaction.atomic
    def remove_service(self, order_service: OrderService):
        self._remove_service(order_service)

    @transaction.atomic
    def place_order(self, data):
        for item in data.get("items", []):
            self.add_item(item.pk, item.units)

        for service in data.get("services", []):
            self.add_service(service.pk, service.units)

        self.transition_to(OrderStatusChoices.ORDER_PLACED)
    
    def cancel_order(self, user: User | None = None, lead: Lead | None = None):
        if not self.current_status:
            raise InvalidOrderTransitionError("Order has no status yet")

        if self.current_status not in self.CANCELLABLE_STATUSES:
            raise InvalidOrderTransitionError(
                f"Order {self.order.code} cannot be cancelled after delivery"
            )

        return self._force_transition(
            OrderStatusChoices.ORDER_CANCELLED,
            user=user,
            lead=lead,
        )
    
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

    def finalize(self):
        return self.transition_to(OrderStatusChoices.FINALIZED)

    def _run_hooks(self, new_status):
        match new_status:
            case OrderStatusChoices.ORDER_PLACED:
                self._on_place_order()
            case OrderStatusChoices.ORDER_CANCELLED:
                self._on_cancel_order()
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
        # Report conversion event
        self.order.lead.change_lead_status(LeadStatusEnum.EVENT_BOOKED, event=self.order)
        
        # Alert client
        self._send_order_placed_confirmation_email()
        
        # Transition to next step in workflow
        self.transition_to(OrderStatusChoices.AWAITING_PREPARATION)

    def _send_order_placed_confirmation_email(self):
        html = render_to_string(
            "emails/order_placed_confirmation.html",
            {
                "full_name": self.lead.full_name,
                "order_code": self.order.code,
                "start_date": self.order.start_date.strftime("%B %d, %Y"),
                "end_date": self.order.end_date.strftime("%B %d, %Y"),
                "company_name": settings.COMPANY_NAME,
            }
        )

        email_service.send_html_email(
            to=self.order.lead.email,
            subject=f"{settings.COMPANY_NAME} -  Order Confirmation Code: {self.order.code}",
            html=html,
        )

    def _on_cancel_order(self):

        # Returen items & add entry to inventory ledger
        for item in self.order.items.all():
            item.inventory.cancel_reservation(order=self.order)

        # Alert client
        self._send_order_cancelled_confirmation_email()
        
    def _send_order_cancelled_confirmation_email(self):
        html = render_to_string(
            "emails/order_cancelled_confirmation.html",
            {
                "full_name": self.lead.full_name,
                "order_code": self.order.code,
                "start_date": self.order.start_date.strftime("%B %d, %Y"),
                "end_date": self.order.end_date.strftime("%B %d, %Y"),
                "company_name": settings.COMPANY_NAME,
            }
        )

        email_service.send_html_email(
            to=self.order.lead.email,
            subject=f"{settings.COMPANY_NAME} -  Order Confirmation Code: {self.order.code}",
            html=html,
        )
    
    def _on_awaiting_preparation(self):
        # place in task queue to be cleared by warehouse staff
        return

    def _on_ready_for_dispatch(self):
        # e.g. assign driver, notify warehouse
        pass

    def _on_dispatched(self):
        # send customer tracking link
        # record action in driver log
        #
        pass

    def _on_delivered(self):
        # send customer picture
        # record action in driver log
        pass

    def _on_picked_up(self):
        for item in self.order.items.all():
            item.inventory.return_items(
                order=self.order,
                target_date=timezone.now().date()
            )
        
        self.finalize()

    def _on_customer_picked_up(self):
        # Items are now physically offsite, but still reserved
        pass
    
    def _on_customer_returned(self):
        for item in self.order.items.all():
            item.inventory.return_items(
                order=self.order,
                target_date=timezone.now().date()
            )
        
        self.finalize()
    
    def _on_finalized(self):
        self._send_review_request()

    def _send_review_request(self):
        review_link = "https://g.page/r/CQaxh0zJ4KNwEAE/review"

        lead = self.order.lead
        event_date = self.order.start_date.date().strftime('%b %d, %Y')

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
    
    def _remove_item(self, order_item: OrderItem):
        order_item.item.inventory.cancel_reservation(order=self.order)

        OrderItemChangeHistory.objects.create(
            user=self.user,
            order=self.order,
            item=order_item.item,
            action=AddedOrRemoveActionChoices.REMOVED,
            units=order_item.units,
            price_per_unit=order_item.price_per_unit,
        )

        order_item.delete()
    
    def _add_item(self, id: int, units: int):
        item = Item.objects.select_for_update().get(pk=id)

        item.inventory.reserve_item(
            order=self.order,
            quantity=units,
        )

        order_item = OrderItem.objects.create(
            order=self.order,
            item=item,
            units=units,
            price_per_unit=item.price,
        )

        OrderItemChangeHistory.objects.create(
            user=self.user,
            order=self.order,
            item=item,
            action=AddedOrRemoveActionChoices.ADDED,
            units=units,
            price_per_unit=item.price,
        )

        return order_item
    
    def _sync_order_items(self, updated_items: list[dict]):
        """
        updated_items = [{"item_id": int, "units": int}]
        """

        existing = {
            oi.item_id: oi
            for oi in self.order.items.select_related("item")
        }

        desired = {
            row["item_id"]: row["units"]
            for row in updated_items
        }

        # Removed items
        for item_id, order_item in existing.items():
            if item_id not in desired:
                self._remove_item(order_item)

        # Added or changed items
        for item_id, units in desired.items():
            if item_id not in existing:
                self._add_item(item_id, units)
            else:
                self._update_item_quantity(existing[item_id], units)
    
    def _add_service(self, id: int, units: int):
        service = Service.objects.get(pk=id)

        order_service = OrderService.objects.create(
            order=self.order,
            service=service,
            units=units,
            price_per_unit=service.price,
        )

        OrderServiceChangeHistory.objects.create(
            user=self.user,
            order=self.order,
            service=service,
            action=AddedOrRemoveActionChoices.ADDED,
            units=units,
            price_per_unit=service.price,
        )

        return order_service
    
    def _remove_service(self, order_service: OrderService):
        service = order_service.service

        OrderServiceChangeHistory.objects.create(
            user=self.user,
            order=self.order,
            service=service,
            action=AddedOrRemoveActionChoices.REMOVED,
            units=order_service.units,
            price_per_unit=order_service.price_per_unit,
        )

        order_service.delete()
    
    def _update_item_quantity(self, order_item, new_units: int):
        old_units = order_item.units
        delta = new_units - old_units

        if delta == 0:
            return

        if delta > 0:
            order_item.item.inventory.reserve_additional_units(
                order=self.order,
                quantity=delta,
            )
        else:
            order_item.item.inventory.release_units(
                order=self.order,
                quantity=abs(delta),
            )

        order_item.units = new_units
        order_item.save(update_fields=["units"])