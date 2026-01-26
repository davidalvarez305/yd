from rest_framework.viewsets import ModelViewSet
from core.models import Item
from api.serializers.item import ItemSerializer

class ItemViewSet(ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer