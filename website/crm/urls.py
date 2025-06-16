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

    # Cocktail Ingredient
    path('cocktail-ingredient/create/', views.CocktailIngredientCreateView.as_view(), name='cocktailingredient_create'),
    path('cocktail-ingredient/<int:pk>/delete/', views.CocktailIngredientDeleteView.as_view(), name='cocktailingredient_delete'),
    
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

    # External Event Detail
    path('event/external/<str:external_id>/', views.ExternalQuoteView.as_view(), name='event_external_detail'),

    # Event Cocktails
    path('event-cocktails/create/', views.EventCocktailCreateView.as_view(), name='eventcocktail_create'),
    path('event-cocktails/<int:pk>/delete/', views.EventCocktailDeleteView.as_view(), name='eventcocktail_delete'),
    
    # Event Staff
    path('event-staff/create/', views.EventStaffCreateView.as_view(), name='eventstaff_create'),
    path('event-staff/<int:pk>/delete/', views.EventStaffDeleteView.as_view(), name='eventstaff_delete'),
    
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
    
    # Ingredient
    path('ingredient/', views.IngredientListView.as_view(), name='ingredient_list'),
    path('ingredient/create/', views.IngredientCreateView.as_view(), name='ingredient_create'),
    path('ingredient/<int:pk>/', views.IngredientDetailView.as_view(), name='ingredient_detail'),
    path('ingredient/<int:pk>/edit/', views.IngredientUpdateView.as_view(), name='ingredient_update'),
    path('ingredient/<int:pk>/delete/', views.IngredientDeleteView.as_view(), name='ingredient_delete'),

    # Shopping List
    path('shopping-list/create/', views.CreateShoppingListView.as_view(), name='eventshoppinglist_create'),
    path('shopping-list/external/<str:external_id>/', views.EventShoppingListExternalDetailView.as_view(), name='eventshoppinglist_external_detail'),

    # Store Item
    path('store-item/', views.StoreItemListView.as_view(), name='storeitem_list'),
    path('store-item/create/', views.StoreItemCreateView.as_view(), name='storeitem_create'),
    path('store-item/<int:pk>/', views.StoreItemDetailView.as_view(), name='storeitem_detail'),
    path('store-item/<int:pk>/edit/', views.StoreItemUpdateView.as_view(), name='storeitem_update'),
    path('store-item/<int:pk>/delete/', views.StoreItemDeleteView.as_view(), name='storeitem_delete'),

    # Quote
    path('quote/create/', views.QuoteCreateView.as_view(), name='quote_create'),
    path('quote/<int:pk>/', views.QuoteDetailView.as_view(), name='quote_detail'),
    path('quote/<int:pk>/edit/', views.QuoteUpdateView.as_view(), name='quote_update'),
    path('quote/<int:pk>/delete/', views.QuoteDeleteView.as_view(), name='quote_delete'),

    # Send Quote Text
    path('quote/<int:pk>/send/', views.QuoteSendView.as_view(), name='quote_send'),

    # External Quote View
    path('external/<str:external_id>/', views.ExternalQuoteView.as_view(), name='external_quote_view'),

    # Quote Services
    path('quote-service/create/', views.QuoteServiceCreateView.as_view(), name='quoteservice_create'),
    path('quote-service/<int:pk>/delete/', views.QuoteServiceDeleteView.as_view(), name='quoteservice_delete'),

    # Quote Preset
    path('quote-preset/', views.QuotePresetListView.as_view(), name='quotepreset_list'),
    path('quote-preset/create/', views.QuotePresetCreateView.as_view(), name='quotepreset_create'),
    path('quote-preset/<int:pk>/', views.QuotePresetDetailView.as_view(), name='quotepreset_detail'),
    path('quote-preset/<int:pk>/edit/', views.QuotePresetUpdateView.as_view(), name='quotepreset_update'),
    path('quote-preset/<int:pk>/delete/', views.QuotePresetDeleteView.as_view(), name='quotepreset_delete'),

    # Quick Quote
    path('quick-quote/create/', views.QuickQuoteCreateView.as_view(), name='quickquote_create'),
]