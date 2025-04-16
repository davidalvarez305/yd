from django.urls import path
from . import views

urlpatterns = [
    path('conversion-log', views.ConversionLogListView.as_view(), name='contact'),
    
    # Visit
    path('visit/', views.VisitListView.as_view(), name='visit_list'),
    path('visit/<int:pk>/edit/', views.VisitUpdateView.as_view(), name='visit_update'),
]