from rest_framework.viewsets import ModelViewSet
from core.models import ItemCategory
from api.serializers.item_category import ItemCategorySerializer

class ItemCategoryViewSet(ModelViewSet):
    queryset = ItemCategory.objects.all()
    serializer_class = ItemCategorySerializer