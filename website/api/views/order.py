from rest_framework.viewsets import ModelViewSet
from core.models import Order
from api.serializers.order import OrderCreateSerializer, OrderSerializer


class OrderViewSet(ModelViewSet):
    queryset = Order.objects.all()

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer