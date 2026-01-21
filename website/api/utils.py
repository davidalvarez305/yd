from rest_framework import serializers
from core.utils import normalize_phone_number

class PhoneNumberField(serializers.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", 32)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        raw = super().to_internal_value(data)
        normalized = normalize_phone_number(raw)

        if not normalized:
            raise serializers.ValidationError("Invalid phone number")

        return normalized