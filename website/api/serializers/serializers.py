from decimal import Decimal
from rest_framework import serializers

from core.models import (
    Order,
    OrderItem,
    OrderService,
    OrderContact,
    OrderBillingContact,
    OrderAddress,
    OrderStatusChangeHistory,
    OrderTask,

    Item,
    ItemCategory,
    Service,

    Address,
    ZipCode,
    City,
    State,

    OrderStatus,
    OrderTaskChoice,
)

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ("state_code", "name")


class CitySerializer(serializers.ModelSerializer):
    state = StateSerializer(read_only=True)

    class Meta:
        model = City
        fields = ("name", "state")


class ZipCodeSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)

    class Meta:
        model = ZipCode
        fields = ("zip_code", "city")


class AddressSerializer(serializers.ModelSerializer):
    zip_code = ZipCodeSerializer(read_only=True)

    class Meta:
        model = Address
        fields = (
            "address_line_1",
            "address_line_2",
            "zip_code",
        )

class ItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCategory
        fields = ("item_category_id", "name")


class ItemSerializer(serializers.ModelSerializer):
    item_category = ItemCategorySerializer(read_only=True)

    class Meta:
        model = Item
        fields = (
            "item_id",
            "name",
            "price",
            "item_category",
        )


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = (
            "service_id",
            "service",
        )

class OrderItemSerializer(serializers.ModelSerializer):
    item = ItemSerializer(read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            "order_item_id",
            "item",
            "units",
            "price_per_unit",
            "total",
        )

    def get_total(self, obj):
        return Decimal(obj.units) * Decimal(obj.price_per_unit)


class OrderServiceSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = OrderService
        fields = (
            "order_service_id",
            "service",
            "units",
            "price_per_unit",
            "total",
        )

    def get_total(self, obj):
        return Decimal(obj.units) * Decimal(obj.price_per_unit)


class OrderContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderContact
        fields = (
            "name",
            "email",
            "phone_number",
        )


class OrderBillingContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderBillingContact
        fields = (
            "name",
            "email",
            "phone_number",
        )


class OrderAddressSerializer(serializers.ModelSerializer):
    address = AddressSerializer(read_only=True)

    class Meta:
        model = OrderAddress
        fields = (
            "order_address_id",
            "stop_type",
            "time_window",
            "start_time",
            "end_time",
            "contact_name",
            "contact_phone",
            "address",
        )

class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = (
            "order_status_id",
            "status",
        )


class OrderStatusChangeSerializer(serializers.ModelSerializer):
    status = OrderStatusSerializer(read_only=True)

    class Meta:
        model = OrderStatusChangeHistory
        fields = (
            "date_created",
            "status",
        )


class OrderTaskChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderTaskChoice
        fields = (
            "task",
        )


class OrderTaskSerializer(serializers.ModelSerializer):
    task = OrderTaskChoiceSerializer(read_only=True)
    user = serializers.StringRelatedField()

    class Meta:
        model = OrderTask
        fields = (
            "order_task_id",
            "task",
            "user",
            "date_created",
        )