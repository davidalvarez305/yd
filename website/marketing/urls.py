from django.urls import path
from . import views

urlpatterns = [
    path('leads/', views.handle_inbound_call, name='call_inbound'),
]