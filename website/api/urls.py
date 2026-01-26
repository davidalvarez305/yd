from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views.order import OrderViewSet
from api.views.item import ItemViewSet
from api.views.item_category import ItemCategoryViewSet

router = DefaultRouter()
router.register(r'order', OrderViewSet, basename='order')
router.register(r'item', ItemViewSet, basename='item')
router.register(r'item-category', ItemCategoryViewSet, basename='item-category')

urlpatterns = [
    path('', include(router.urls)),
]