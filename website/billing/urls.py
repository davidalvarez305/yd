from django.urls import path
from . import views

urlpatterns = [
    path('stripe/success', views.handle_successful_payment, name='successful_payment'),
    path('initiate-checkout', views.handle_initiate_checkout, name='initiate_checkout'),
]