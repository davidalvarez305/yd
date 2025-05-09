from django.urls import path
from . import views

urlpatterns = [
    path('calls/inbound', views.handle_inbound_call, name='call_inbound'),
    path('calls/outbound', views.handle_outbound_call, name='call_outbound'),
    path('calls/end/status', views.handle_call_status_callback, name='call_status_callback'),
    path('calls/end/recording', views.handle_call_recording_callback, name='call_recording_callback'),
    path('message/inbound', views.handle_inbound_message, name='inbound_message'),
    path('message/outbound', views.MessageCreateView.as_view(), name='outbound_message'),
    path('message/end/status', views.handle_message_status_callback, name='message_status_callback'),
]