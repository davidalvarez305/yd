from django.urls import path

from marketing import views as marketing_views

urlpatterns = [
    # Call Tracking
    path('call-tracking/', marketing_views.CallTrackingNumberListView.as_view(), name='calltrackingnumber_list'),
    path('call-tracking/create/', marketing_views.CallTrackingNumberCreateView.as_view(), name='calltrackingnumber_create'),
    path('call-tracking/<int:pk>/', marketing_views.CallTrackingNumberDetailView.as_view(), name='calltrackingnumber_detail'),
    path('call-tracking/<int:pk>/edit/', marketing_views.CallTrackingNumberUpdateView.as_view(), name='calltrackingnumber_update'),
    path('call-tracking/<int:pk>/delete/', marketing_views.CallTrackingNumberDeleteView.as_view(), name='calltrackingnumber_delete'),
    
    # Lead
    path('lead/', marketing_views.LeadListView.as_view(), name='lead_list'),
    path('lead/<int:pk>/', marketing_views.LeadDetailView.as_view(), name='lead_detail'),
    path('lead/<int:pk>/edit/', marketing_views.LeadUpdateView.as_view(), name='lead_update'),
    path('lead/<int:pk>/delete/', marketing_views.LeadDeleteView.as_view(), name='lead_delete'),
]