from django.urls import path
from . import views

urlpatterns = [
    path('calls/inbound', views.handle_inbound_call, name='call_inbound'),
    path('message/inbound', views.handle_inbound_message, name='inbound_message'),
    path('message/outbound', views.MessageCreateView.as_view(), name='outbound_message'),
]