from django.urls import path

from marketing import views as marketing_views

urlpatterns = [
    path('call-tracking/', marketing_views.CallTrackingNumberListView.as_view(), name='calltrackingnumber_list'),
    path('call-tracking/create/', marketing_views.CallTrackingNumberCreateView.as_view(), name='calltrackingnumber_create'),
    path('call-tracking/<int:pk>/', marketing_views.CallTrackingNumberDetailView.as_view(), name='calltrackingnumber_detail'),
    path('call-tracking/<int:pk>/edit/', marketing_views.CallTrackingNumberUpdateView.as_view(), name='calltrackingnumber_update'),
    path('call-tracking/<int:pk>/delete/', marketing_views.CallTrackingNumberDeleteView.as_view(), name='calltrackingnumber_delete'),
]