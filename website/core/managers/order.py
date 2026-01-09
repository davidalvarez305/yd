from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from django.db import transaction
from django.db.models import Exists, OuterRef, Count, Max
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.template.loader import render_to_string
from website import settings

from core.email import email_service
from core.models import AddedOrRemoveActionChoices, DriverRoute, DriverStop, DriverStopStatus, DriverStopStatusChangeHistory, DriverStopStatusChoices, Item, Lead, LeadStatusEnum, Message, OrderAddressTypeChoices, OrderItem, OrderItemChangeHistory, OrderService, OrderServiceChangeHistory, OrderStatus, OrderStatusChangeHistory, OrderStatusChoices, OrderTask, OrderTaskChoices, OrderTaskLog, OrderTaskStatus, OrderTaskStatusChoices, PhoneCallTranscription, RouteZone, Service, User, UserRoleChoices
from core.messaging import messaging_service
from core.ai import ai_agent
from core.delivery import delivery_service

@dataclass
class TransitionContext:
    user: Optional[User] = None
    driver_stop: Optional[DriverStop] = None
    source: str = "system"
    metadata: Dict[str, Any] = field(default_factory=dict)

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
    def transition_to(self, new_status: str, *, context: TransitionContext | None = None):
        context = context or TransitionContext()

        if self.current_status and not self.can_transition_to(new_status):
            raise InvalidOrderTransitionError(
                f"Cannot transition order {self.order.code} "
                f"from '{self.current_status}' to '{new_status}'"
            )

        status = OrderStatus.objects.get(status=new_status)

        self.order.status = status
        self.order.save(update_fields=["status"])

        OrderStatusChangeHistory.objects.create(
            order=self.order,
            status=status,
            user=context.user,
        )

        self._run_hooks(new_status, context)
    
    @transaction.atomic
    def _force_transition(self, new_status: str, *, context: TransitionContext | None = None):
        context = context or TransitionContext()

        status = OrderStatus.objects.get(status=new_status)

        self.order.status = status
        self.order.save(update_fields=["status"])

        OrderStatusChangeHistory.objects.create(
            order=self.order,
            status=status,
            user=context.user,
            lead=context.lead,
        )

        self._run_hooks(new_status, context)
    
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
    
    def cancel_order(self, user: User | None = None):
        if not self.current_status:
            raise InvalidOrderTransitionError("Order has no status yet")

        if self.current_status not in self.CANCELLABLE_STATUSES:
            raise InvalidOrderTransitionError(
                f"Order {self.order.code} cannot be cancelled after delivery"
            )

        return self._force_transition(
            OrderStatusChoices.ORDER_CANCELLED,
            context=TransitionContext(
                user=user,
                source="user",
                user=user,
            )
        )
    
    def mark_ready_for_dispatch(self):
        return self.transition_to(OrderStatusChoices.READY_FOR_DISPATCH)

    def dispatch(self, *, driver_stop: DriverStop, user: User | None = None):
        return self.transition_to(
            OrderStatusChoices.DISPATCHED,
            context=TransitionContext(
                user=user,
                driver_stop=driver_stop,
                source="driver"
            )
        )

    def mark_delivered(self):
        return self.transition_to(OrderStatusChoices.DELIVERED)

    def mark_pending_pickup(self):
        return self.transition_to(OrderStatusChoices.PENDING_PICK_UP)
    
    def customer_picked_up(self):
        return self.transition_to(OrderStatusChoices.CUSTOMER_PICKED_UP)
    
    def customer_returned(self):
        return self.transition_to(OrderStatusChoices.CUSTOMER_RETURNED)

    def pickup_completed(self):
        return self.transition_to(OrderStatusChoices.PICKED_UP)

    def finalize(self):
        return self.transition_to(OrderStatusChoices.FINALIZED)

    def _run_hooks(self, new_status, context: TransitionContext):
        match new_status:
            case OrderStatusChoices.ORDER_PLACED:
                self._on_place_order(context)
            case OrderStatusChoices.ORDER_CANCELLED:
                self._on_cancel_order(context)
            case OrderStatusChoices.AWAITING_PREPARATION:
                self._on_awaiting_preparation(context)
            case OrderStatusChoices.READY_FOR_DISPATCH:
                self._on_ready_for_dispatch(context)
            case OrderStatusChoices.DISPATCHED:
                self._on_dispatched(context)
            case OrderStatusChoices.DELIVERED:
                self._on_delivered(context)
            case OrderStatusChoices.PICKED_UP:
                self._on_picked_up(context)
            case OrderStatusChoices.CUSTOMER_PICKED_UP:
                self._on_customer_picked_up(context)
            case OrderStatusChoices.CUSTOMER_RETURNED:
                self._on_customer_returned(context)
            case OrderStatusChoices.FINALIZED:
                self._on_finalized(context)

    def _on_place_order(self, context: TransitionContext):
        # Report conversion event
        self.order.lead.change_lead_status(LeadStatusEnum.EVENT_BOOKED, event=self.order)
        
        # Alert client
        self._send_order_placed_confirmation_email()
        
        # Transition to next step in workflow
        self.transition_to(OrderStatusChoices.AWAITING_PREPARATION, context=TransitionContext(source="system"))

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
        order_task = OrderTask.objects.get(task=OrderTaskChoices.LOAD_ORDER_ITEMS)
        order_task_status = OrderTaskStatus.objects.get(status=OrderTaskStatusChoices.ASSIGNED)
        user = User.objects.filter(roles__role=UserRoleChoices.WAREHOUSE_STAFF).first()

        OrderTaskLog.objects.create(
            order_task=order_task,
            order=self.order,
            order_task_status=order_task_status,
            assigned_to=user,
        )

    def _on_ready_for_dispatch(self):

        stop_type = OrderAddressTypeChoices.DELIVERY

        # query available driver
        driver_route = self._assign_driver_route_for_order(stop_type=stop_type)

        # get delivery address
        order_address = self.order.addresses.filter(stop_type=stop_type).first()

        # assign driver
        stop = DriverStop(
            driver_route=driver_route,
            order_address=order_address,
        )

        stop.save()

        # create plan
        plan = delivery_service.create_plan(data=data)
        
        # add stop
        route_stop = plan.add_stop(stop=stop)
        stop.external_id = route_stop.external_id
        stop.web_tracking_link = route_stop.web_tracking_link

        stop.save()

        # notify user that truck will be arriving at X - Y time window
        self._send_order_ready_for_dispatch_email()

    def _on_dispatched(self, context: TransitionContext):
        driver_stop = context.driver_stop
        if not driver_stop:
            raise RuntimeError("DISPATCHED requires driver_stop in context")

        self._send_user_dispatch_with_live_tracking_link()

        status = DriverStopStatus.objects.get(status=DriverStopStatusChoices.OUT_FOR_DELIVERY)

        DriverStopStatusChangeHistory.objects.create(
            driver_stop=driver_stop,
            driver_stop_status=status,
        )

    def _on_delivered(self, context: TransitionContext):
        driver_stop = context.driver_stop
        if not driver_stop:
            raise RuntimeError("DELIVERED requires driver_stop")

        self._send_user_delivery_confirmation()

        status = DriverStopStatus.objects.get(status=DriverStopStatusChoices.COMPLETED)

        DriverStopStatusChangeHistory.objects.create(
            driver_stop=driver_stop,
            driver_stop_status=status,
        )

    def _on_picked_up(self, context: TransitionContext):
        driver_stop = context.driver_stop
        if not driver_stop:
            raise RuntimeError("PICKED_UP requires driver_stop")

        self._send_user_pick_up_confirmation()

        status = DriverStopStatus.objects.get(
            status=DriverStopStatusChoices.COMPLETED
        )

        DriverStopStatusChangeHistory.objects.create(
            driver_stop=driver_stop,
            driver_stop_status=status,
        )

        for item in self.order.items.all():
            item.inventory.return_items(
                order=self.order,
                target_date=timezone.now().date()
            )

        self.transition_to(
            OrderStatusChoices.FINALIZED,
            context=TransitionContext(source="system")
        )

    def _on_customer_picked_up(self):
       self._send_customer_pickup_confirmation_email()
    
    def _on_customer_returned(self):
        
        # send customer notification e-mail
        self._send_customer_return_confirmation_email()

        # record action in inventory ledger
        for item in self.order.items.all():
            item.inventory.return_items(
                order=self.order,
                target_date=timezone.now().date()
            )
        
        # finalize order status
        self.finalize()
    
    def _on_pending_pick_up():
        return
    
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
    
    @transaction.atomic
    def _assign_driver_route_for_order(self, stop_type):
        
        # Resolve delivery address
        order_address = (
            self.order.addresses
            .select_related("address__zip_code")
            .filter(stop_type=stop_type)
            .first()
        )

        if not order_address:
            raise ValidationError("Order has no address")

        zip_code = order_address.address.zip_code

        # Resolve route zone
        try:
            route_zone = RouteZone.objects.select_for_update().get(zip_code=zip_code)
        except RouteZone.DoesNotExist:
            raise ValidationError(f"No route zone configured for ZIP {zip_code}")

        target_date = self.order.start_date.date()

        # 3️⃣ Try to reuse ANY existing route with capacity
        existing_route = (
            DriverRoute.objects
            .select_for_update()
            .annotate(stop_count=Count("stops"))
            .filter(
                route_zone=route_zone,
                target_date=target_date,
            )
            .order_by("date_created")
            .first()
        )

        if existing_route and existing_route.stop_count < existing_route.user.max_daily_stops:
            return existing_route

        # Find next available driver (round-robin)
        available_driver = (
            User.objects
            .filter(roles__role=UserRoleChoices.DRIVER)
            .annotate(
                has_route_today=Exists(
                    DriverRoute.objects.filter(
                        user=OuterRef("pk"),
                        target_date=target_date,
                    )
                ),
                last_assigned=Max("driver_routes__date_created"),
            )
            .filter(has_route_today=False)
            .order_by("last_assigned", "id")
            .first()
        )

        if not available_driver:
            raise ValidationError("No available drivers for this date")
        
        title = f"Order #{self.order.order_code} - {target_date.strftime('%m/%d/%Y')}"

        data = delivery_service.create_route(
            route_date=target_date,
            title=title,
            drivers=drivers,
        )
        
        return DriverRoute.objects.create(
            external_id=data.get('id'),
            user=available_driver,
            route_zone=route_zone,
            target_date=target_date,
        )