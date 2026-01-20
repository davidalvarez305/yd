from rest_framework import serializers
from core.models import Item, LeadMarketing, OrderAddressTypeChoices, Service, ZipCode, Order, Address, OrderAddress
from django.db import transaction
from django.utils.dateparse import parse_datetime

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ("order_id", "code", "date_created")

class OrderItemInputSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    units = serializers.IntegerField(min_value=1)

class OrderServiceInputSerializer(serializers.Serializer):
    service_id = serializers.IntegerField()
    units = serializers.IntegerField(min_value=1)

class OrderAddressInputSerializer(serializers.Serializer):
    street_address = serializers.CharField()
    zip_code = serializers.PrimaryKeyRelatedField(queryset=ZipCode.objects.select_related("city__state"))
    delivery_type = serializers.ChoiceField(choices=OrderAddress._meta.get_field("stop_type").choices)
    delivery_start_time = serializers.DateTimeField(required=False, allow_null=True)
    delivery_end_time = serializers.DateTimeField(required=False, allow_null=True)

class OrderCreateSerializer(serializers.ModelSerializer):
    pickup = OrderAddressInputSerializer(required=False)
    delivery = OrderAddressInputSerializer(required=False)

    items = OrderItemInputSerializer(many=True, required=True)
    services = OrderServiceInputSerializer(many=True, required=True)

    class Meta:
        model = Order
        exclude = (
            "order_id",
            "code",
            "date_created",
            "has_delivery",
            "lead",
            "user"
        )

    def validate(self, attrs):
        pickup = attrs.get("pickup")
        delivery = attrs.get("delivery")

        if delivery and not pickup:
            raise serializers.ValidationError(
                "Pickup address is required when delivery is provided."
            )

        if pickup and not delivery:
            raise serializers.ValidationError(
                "Pickup without delivery is not allowed."
            )

        if not attrs.get("items") and not attrs.get("services"):
            raise serializers.ValidationError(
                "At least one item or service is required."
            )

        return attrs

    def _build_address(self, data, order, stop_type):
        address, _ = Address.objects.get_or_create(
            address_line_1=data.get('street_address'),
            address_line_2=data.get('address_line_2'),
            zip_code=data.get('zip_code'),
        )

        OrderAddress.objects.create(
            order=order,
            address=address,
            stop_type=stop_type,
            delivery_start_time=data.get('delivery_start_time'),
            delivery_end_time=data.get('delivery_end_time'),
        )

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")

        user = None

        if request and request.user and request.user.is_authenticated:
            user = request.user

        delivery = validated_data.pop("delivery")
        pickup = validated_data.pop("pickup")
        items = validated_data.pop("items", [])
        services = validated_data.pop("services", [])
        has_delivery = bool(delivery and pickup)

        order = Order.objects.create(
            **validated_data,
            has_delivery=has_delivery,
        )

        if pickup and delivery:
            self._build_address(
                delivery,
                order,
                stop_type=OrderAddressTypeChoices.DELIVERY,
            )

            self._build_address(
                pickup,
                order,
                stop_type=OrderAddressTypeChoices.PICKUP,
            )

        order.manager.place_order(
            items=items,
            services=services,
            user=user,
        )

        return order