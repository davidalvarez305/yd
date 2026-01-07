from datetime import _Date
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum, Case, When, IntegerField, F, Window, Min, Value
from django.db.models.functions import Coalesce

from core.models import Item, ItemState, ItemStateChangeHistory, ItemStateChoices, Order


AVAILABILITY_DELTA = Case(
    When(state__state__in=[
        ItemStateChoices.PURCHASED,
        ItemStateChoices.RETURNED,
    ], then=F('quantity')),
    When(state__state__in=[
        ItemStateChoices.RESERVED,
        ItemStateChoices.SOLD,
        ItemStateChoices.DECOMMISSIONED,
    ], then=-F('quantity')),
    default=0,
    output_field=IntegerField(),
)

class ItemInventoryManager:
    """
    Ledger-based inventory manager.
    All inventory mutations MUST go through this class.
    """

    def __init__(self, item: Item):
        self.item = item

    def available_units_on_date(self, on_date):
        result = self.item.state_changes.filter(
            target_date__lte=on_date,
        ).aggregate(
            total=Sum(AVAILABILITY_DELTA)
        )

        return result['total'] or 0

    def available_units_for_range(self, start_date, end_date):
        qs = (
            self.item.state_changes
            .filter(target_date__lt=end_date)
            .annotate(delta=AVAILABILITY_DELTA)
            .values('target_date')
            .annotate(day_delta=Sum('delta'))
            .order_by('target_date')
            .annotate(
                running_total=Window(
                    expression=Sum('day_delta'),
                    order_by=F('target_date').asc(),
                )
            )
            .filter(target_date__gte=start_date)
            .aggregate(
                min_available=Coalesce(Min('running_total'), 0)
            )
        )

        return qs['min_available']
    
    @transaction.atomic
    def reserve_item(self, order: Order):
        Item.objects.select_for_update().get(pk=self.item.pk)
        booked_item = order.items.filter(item=self.item).first()
        if not booked_item:
            raise ValidationError("Item not found on order")
        available = self.available_units_for_range(order.start_date.date(), order.end_date.date())

        if available < booked_item.units:
            raise ValidationError(
                f"Only {available} units available for selected dates"
            )

        state = ItemState.objects.get(state=ItemStateChoices.RESERVED)

        ItemStateChangeHistory.objects.create(
            item=self.item,
            order=order,
            state=state,
            quantity=booked_item.units,
            target_date=order.start_date.date(),
        )
    
    @transaction.atomic
    def return_items(self, order: Order, target_date: _Date):
        Item.objects.select_for_update().get(pk=self.item.pk)
        booked_item = order.items.filter(item=self.item).first()
        if not booked_item:
            raise ValidationError("Item not found on order")
        state = ItemState.objects.get(state=ItemStateChoices.RETURNED)

        ItemStateChangeHistory.objects.create(
            item=self.item,
            order=order,
            state=state,
            quantity=booked_item.units,
            target_date=target_date,
        )
    
    @transaction.atomic
    def cancel_reservation(self, order: Order):
        reservation = (
            ItemStateChangeHistory.objects
            .select_for_update()
            .get(
                item=self.item,
                order=order,
                state__state=ItemStateChoices.RESERVED,
            )
        )

        state = ItemState.objects.get(state=ItemStateChoices.RETURNED)

        ItemStateChangeHistory.objects.create(
            item=self.item,
            order=order,
            state=state,
            quantity=reservation.quantity,
            target_date=reservation.target_date,
        )
    
    @transaction.atomic
    def purchase(self, quantity: int, target_date: _Date):
        state = ItemState.objects.get(state=ItemStateChoices.PURCHASED)

        ItemStateChangeHistory.objects.create(
            item=self.item,
            state=state,
            quantity=quantity,
            target_date=target_date,
        )
    
    @transaction.atomic
    def decommission(self, quantity: int, target_date: _Date):
        state = ItemState.objects.get(state=ItemStateChoices.DECOMMISSIONED)

        ItemStateChangeHistory.objects.create(
            item=self.item,
            state=state,
            quantity=quantity,
            target_date=target_date,
        )