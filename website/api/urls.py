from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views.order import OrderViewSet
from api.views.item import ItemViewSet
from api.views.service import ServiceViewSet
from api.views.item_category import ItemCategoryViewSet
from api.views.inventory import ItemStateChangeHistoryViewSet

router = DefaultRouter()
router.register(r'order', OrderViewSet, basename='order')
router.register(r'item', ItemViewSet, basename='item')
router.register(r'inventory', ItemStateChangeHistoryViewSet, basename='inventory')
router.register(r'item-category', ItemCategoryViewSet, basename='item-category')
router.register(r'service', ServiceViewSet, basename='service')

urlpatterns = [
    path('', include(router.urls)),
]