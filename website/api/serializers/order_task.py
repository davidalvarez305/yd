from rest_framework import serializers
from core.models import OrderTask, OrderTaskStatusChoices
from core.managers.order_task import InvalidTaskTransitionError

class OrderTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderTask
        fields = "__all__"

class OrderTaskStartSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(
        choices=[OrderTaskStatusChoices.IN_PROGRESS],
        write_only=True,
        required=True,
    )

    class Meta:
        model = OrderTask
        fields = ("status",)

    def update(self, instance: OrderTask, validated_data):
        request = self.context.get("request")
        user = request.user if request else None

        if not user:
            raise serializers.ValidationError("User context is required")

        try:
            instance.manager.transition_to(
                OrderTaskStatusChoices.IN_PROGRESS,
                user=user,
            )
        except InvalidTaskTransitionError as e:
            raise serializers.ValidationError(str(e))

        return instance

class OrderTaskCompleteSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(
        choices=[OrderTaskStatusChoices.COMPLETED],
        write_only=True,
        required=True,
    )

    class Meta:
        model = OrderTask
        fields = ("status",)

    def update(self, instance: OrderTask, data):
        request = self.context.get("request")
        user = request.user if request else None

        if not user:
            raise serializers.ValidationError("User context is required")

        try:
            instance.manager.complete_task(user=user)
        except InvalidTaskTransitionError as e:
            raise serializers.ValidationError(str(e))

        return instance