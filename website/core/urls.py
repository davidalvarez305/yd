from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('contact', views.ContactView.as_view(), name='contact'),
    path('login', views.LoginView.as_view(), name='login'),
    path('privacy-policy', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('terms-and-conditions', views.TermsAndConditionsView.as_view(), name='terms_and_conditions'),
    path('robots.txt', views.RobotsTxtView.as_view(), name='robots_txt'),
    path('quote', views.QuoteView.as_view(), name='quote'),
    path('logout', views.LogoutView.as_view(), name='logout')
]