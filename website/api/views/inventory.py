from rest_framework.viewsets import ModelViewSet
from core.models import ItemStateChangeHistory
from api.serializers.inventory import ItemStateChangeHistorySerializer

class ItemStateChangeHistoryViewSet(ModelViewSet):
    queryset = ItemStateChangeHistory.objects.all()
    serializer_class = ItemStateChangeHistorySerializer