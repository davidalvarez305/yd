from django.urls import path
from . import views

urlpatterns = [
    path('message/inbound', views.handle_inbound_message, name='inbound_message'),
    path('message/outbound', views.handle_outbound_message, name='outbound_message'),
]