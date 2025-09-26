from django.urls import path
from . import views

urlpatterns = [

    # Calls
    path('calls/inbound', views.handle_inbound_call, name='call_inbound'),
    path('calls/outbound', views.OutboundCallView.as_view(), name='call_outbound'),
    path('calls/outbound/status', views.handle_outbound_call_status_callback, name='call_outbound_status_callback'),
    path('calls/end/status', views.handle_call_status_callback, name='call_status_callback'),
    path('calls/end/recording', views.handle_call_recording_callback, name='call_recording_callback'),

    # Tracking Calls
    path('calls/tracking/inbound', views.handle_inbound_tracking_call, name='inbound_tracking_call'),
    path('calls/tracking/inbound/end', views.handle_inbound_tracking_call_end, name='inbound_tracking_call_end'),
    path('message/tracking/inbound', views.handle_inbound_tracking_message, name='inbound_tracking_message'),

    # Text SMS
    path('message/inbound', views.handle_inbound_message, name='inbound_message'),
    path('message/outbound', views.MessageCreateView.as_view(), name='outbound_message'),
    path('message/end/status', views.handle_message_status_callback, name='message_status_callback'),
    
    # Transcription
    path('transcription/callback', views.handle_transcription_subcription_callback, name='transcriptipn_callback')
]