from django.urls import path
from core import views

urlpatterns = [
    path('message/inbound', views.handle_inbound_message, name='inbound_message'),
    path('message/outbound', views.OutboundMessage.as_view(), name='outbound_message'),
]