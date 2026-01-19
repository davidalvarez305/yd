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
    zip_code = serializers.PrimaryKeyRelatedField(
        queryset=ZipCode.objects.select_related("city__state")
    )
    delivery_type = serializers.ChoiceField(
        choices=OrderAddress._meta.get_field("stop_type").choices
    )
    delivery_start_time = serializers.CharField(required=False, allow_null=True)
    delivery_end_time = serializers.CharField(required=False, allow_null=True)

    def parse_times(self, data):
        start = parse_datetime(data.get("delivery_start_time"))
        end = parse_datetime(data.get("delivery_end_time"))

        if data.get("delivery_start_time") and not start:
            raise serializers.ValidationError("Invalid delivery_start_time")

        if data.get("delivery_end_time") and not end:
            raise serializers.ValidationError("Invalid delivery_end_time")

        return start, end

class OrderCreateSerializer(serializers.ModelSerializer):
    pickup = serializers.DictField(required=False)
    delivery = serializers.DictField(required=False)

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
        zip_code = ZipCode.objects.select_related("city__state").get(
            code=data["zip_code"]
        )

        start = parse_datetime(data.get("delivery_start_time"))
        end = parse_datetime(data.get("delivery_end_time"))

        if data.get("delivery_start_time") and not start:
            raise serializers.ValidationError("Invalid delivery_start_time")

        if data.get("delivery_end_time") and not end:
            raise serializers.ValidationError("Invalid delivery_end_time")

        address = Address.objects.create(
            street_address=data["street_address"],
            zip_code=zip_code,
            city=zip_code.city,
            state=zip_code.city.state,
        )

        OrderAddress.objects.create(
            order=order,
            address=address,
            stop_type=stop_type,
            delivery_start_time=start,
            delivery_end_time=end,
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