from rest_framework import serializers
from core.models import Item, Lead, LeadStatusEnum, OrderAddressTypeChoices, OrderContact, OrderBillingContact, Service, ZipCode, Order, Address, OrderAddress
from django.db import transaction

from api.utils import PhoneNumberField

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ("order_id", "code", "date_created")

class OrderBillingContactInputSerialier(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone_number = PhoneNumberField()
    street_address_one = serializers.CharField(max_length=255)
    street_address_two = serializers.CharField(max_length=255)
    zip_code = serializers.PrimaryKeyRelatedField(queryset=ZipCode.objects.select_related("city__state"))

class OrderContactInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    phone_number = PhoneNumberField()

class OrderItemInputSerializer(serializers.Serializer):
    item = serializers.PrimaryKeyRelatedField(queryset=Item.objects.all())
    units = serializers.IntegerField(min_value=1)

class OrderServiceInputSerializer(serializers.Serializer):
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all())
    units = serializers.IntegerField(min_value=1)

class OrderAddressInputSerializer(serializers.Serializer):
    street_address_one = serializers.CharField(max_length=255)
    street_address_two = serializers.CharField(max_length=255)
    zip_code = serializers.PrimaryKeyRelatedField(queryset=ZipCode.objects.select_related("city__state"))
    delivery_type = serializers.ChoiceField(choices=OrderAddress._meta.get_field("stop_type").choices)
    delivery_start_time = serializers.DateTimeField(required=False, allow_null=True)
    delivery_end_time = serializers.DateTimeField(required=False, allow_null=True)

class OrderCreateSerializer(serializers.ModelSerializer):
    pickup = OrderAddressInputSerializer(required=False, write_only=True)
    delivery = OrderAddressInputSerializer(required=False, write_only=True)
    items = OrderItemInputSerializer(many=True, write_only=True)
    services = OrderServiceInputSerializer(many=True, write_only=True)
    order_contact = OrderContactInputSerializer(required=True)
    billing_contact = OrderBillingContactInputSerialier(required=True)

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
            address_line_1=data["street_address_one"],
            address_line_2=data.get("street_address_two", ""),
            zip_code=data["zip_code"],
        )

        OrderAddress.objects.create(
            order=order,
            address=address,
            stop_type=stop_type,
            delivery_start_time=data.get("delivery_start_time"),
            delivery_end_time=data.get("delivery_end_time"),
        )

    def _build_lead(self, data):
        request = self.context.get('request')
        phone_number = data.get('phone_number')
        full_name = data.get('name')

        lead = Lead.objects.filter(phone_number=phone_number).first()
        if lead:
            return lead

        lead = Lead.objects.create(full_name=full_name, phone_number=phone_number)

        if request:
            lead.attach_marketing_data(request=request)

        lead.change_lead_status(status=LeadStatusEnum.LEAD_CREATED)

        return lead

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")

        user = None

        if request and request.user and request.user.is_authenticated:
            user = request.user

        billing_contact_data = validated_data.pop("billing_contact")
        order_contact_data = validated_data.pop("order_contact")
        lead = self._build_lead(billing_contact_data)
        delivery = validated_data.pop("delivery")
        pickup = validated_data.pop("pickup")
        items = validated_data.pop("items", [])
        services = validated_data.pop("services", [])
        has_delivery = bool(delivery and pickup)

        order = Order.objects.create(
            **validated_data,
            user=user,
            lead=lead,
            has_delivery=has_delivery,
        )

        OrderContact.objects.create(
            order=order,
            **order_contact_data,
        )

        OrderBillingContact.objects.create(
            order=order,
            **billing_contact_data,
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