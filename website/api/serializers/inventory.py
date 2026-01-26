from rest_framework import serializers
from core.models import ItemStateChangeHistory

class ItemStateChangeHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemStateChangeHistory
        fields = "__all__"