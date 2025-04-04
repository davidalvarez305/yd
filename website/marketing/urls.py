from django.urls import path
from . import views

urlpatterns = [
    path('conversion-log', views.ConversionLogListView.as_view(), name='contact'),
]