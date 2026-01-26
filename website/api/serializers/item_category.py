from rest_framework import serializers
from core.models import ItemCategory

class ItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCategory
        fields = "__all__"