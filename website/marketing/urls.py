from django.urls import path
from . import views

urlpatterns = [
    path('facebook/leads/', views.handle_facebook_create_new_lead, name='facebook_leads_webhook'),
]