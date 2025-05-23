from django.urls import path

from . import views

urlpatterns = [
    # Chat
    path('chat', views.LeadChatView.as_view(), name='chat'),
    path('chat/messages/<int:pk>/', views.LeadChatMessagesView.as_view(), name='chat_messages'),

    # Call Tracking
    path('call-tracking/', views.CallTrackingNumberListView.as_view(), name='calltrackingnumber_list'),
    path('call-tracking/create/', views.CallTrackingNumberCreateView.as_view(), name='calltrackingnumber_create'),
    path('call-tracking/<int:pk>/', views.CallTrackingNumberDetailView.as_view(), name='calltrackingnumber_detail'),
    path('call-tracking/<int:pk>/edit/', views.CallTrackingNumberUpdateView.as_view(), name='calltrackingnumber_update'),
    path('call-tracking/<int:pk>/delete/', views.CallTrackingNumberDeleteView.as_view(), name='calltrackingnumber_delete'),
    
    # Lead
    path('lead/', views.LeadListView.as_view(), name='lead_list'),
    path('lead/<int:pk>/', views.LeadDetailView.as_view(), name='lead_detail'),
    path('lead/<int:pk>/edit/', views.LeadUpdateView.as_view(), name='lead_update'),
    path('lead/<int:pk>/archive/', views.LeadArchiveView.as_view(), name='lead_archive'),

    # Lead Marketing
    path('lead-marketing/<int:pk>/edit/', views.LeadMarketingUpdateView.as_view(), name='lead_marketing_update'),
    
    # Cocktail
    path('cocktail/', views.CocktailListView.as_view(), name='cocktail_list'),
    path('cocktail/create/', views.CocktailCreateView.as_view(), name='cocktail_create'),
    path('cocktail/<int:pk>/', views.CocktailDetailView.as_view(), name='cocktail_detail'),
    path('cocktail/<int:pk>/edit/', views.CocktailUpdateView.as_view(), name='cocktail_update'),
    path('cocktail/<int:pk>/delete/', views.CocktailDeleteView.as_view(), name='cocktail_delete'),
    
    # Service
    path('service/', views.ServiceListView.as_view(), name='service_list'),
    path('service/create/', views.ServiceCreateView.as_view(), name='service_create'),
    path('service/<int:pk>/', views.ServiceDetailView.as_view(), name='service_detail'),
    path('service/<int:pk>/edit/', views.ServiceUpdateView.as_view(), name='service_update'),
    path('service/<int:pk>/delete/', views.ServiceDeleteView.as_view(), name='service_delete'),
    
    # User
    path('user/', views.UserListView.as_view(), name='user_list'),
    path('user/create/', views.UserCreateView.as_view(), name='user_create'),
    path('user/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('user/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_update'),
    path('user/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    
    # Event
    path('event/', views.EventListView.as_view(), name='event_list'),
    path('event/create/', views.EventCreateView.as_view(), name='event_create'),
    path('event/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('event/<int:pk>/edit/', views.EventUpdateView.as_view(), name='event_update'),
    path('event/<int:pk>/delete/', views.EventDeleteView.as_view(), name='event_delete'),
    
    # Message
    path('message/', views.MessageListView.as_view(), name='message_list'),
    path('message/<int:pk>/', views.MessageDetailView.as_view(), name='message_detail'),
    path('message/<int:pk>/edit/', views.MessageUpdateView.as_view(), name='message_update'),
    
    # Phone Call
    path('phone-call/', views.PhoneCallListView.as_view(), name='phonecall_list'),
    path('phone-call/<int:pk>/', views.PhoneCallDetailView.as_view(), name='phonecall_detail'),
    path('phone-call/<int:pk>/edit/', views.PhoneCallUpdateView.as_view(), name='phonecall_update'),

    # HTTP Logs
    path('log', views.HTTPLogListView.as_view(), name='log'),
    
    # Visit
    path('visit/', views.VisitListView.as_view(), name='visit_list'),
    path('visit/<int:pk>/edit/', views.VisitUpdateView.as_view(), name='visit_update'),

    # Lead Note
    path('lead-note/create/', views.LeadNoteCreateView.as_view(), name='leadnote_create'),
    path('lead-note/<int:pk>/', views.LeadNoteDetailView.as_view(), name='leadnote_detail'),
    path('lead-note/<int:pk>/edit/', views.LeadNoteUpdateView.as_view(), name='leadnote_update'),
    path('lead-note/<int:pk>/delete/', views.LeadNoteDeleteView.as_view(), name='leadnote_delete'),
]