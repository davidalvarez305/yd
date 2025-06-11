from django.urls import path
from . import views

urlpatterns = [
    path('stripe/success', views.handle_successful_payment, name='successful_payment'),
    path('checkout/lead/<int:pk>/', views.handle_initiate_checkout, name='initiate_checkout'),
]