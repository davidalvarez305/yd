from django.urls import path
from . import views

urlpatterns = [
    path('stripe/success', views.handle_payment_webhook, name='successful_payment'),
    path('initiate-checkout', views.handle_initiate_payment, name='initiate_checkout'),
]