from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('contact', views.ContactView.as_view(), name='contact'),
    path('login', views.LoginView.as_view(), name='login'),
    path('privacy-policy', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('terms-and-conditions', views.TermsAndConditionsView.as_view(), name='terms_and_conditions'),
    path('robots.txt', views.RobotsTxtView.as_view(), name='robots_txt'),
    path('lead', views.LeadCreateView.as_view(), name='lead_create'),
    path('logout', views.LogoutView.as_view(), name='logout'),
    path('thank-you/<str:external_id>/', views.SuccessPaymentView.as_view(), name='success_payment'),
    path('cancel/<str:external_id>/', views.SuccessPaymentView.as_view(), name='cancel_payment'),
    path('external/<str:external_id>/', views.redirect_external, name='redirect_external'),

    # Landing Pages
    path('chair-rentals/', views.ChairRentals.as_view(), name='chair-rentals'),
    path('table-rentals/', views.TableRentals.as_view(), name='table-rentals'),
    path('tent-rentals/', views.TentRentals.as_view(), name='tent-rentals'),
    path('bar-rentals/', views.BarRentals.as_view(), name='bar-rentals'),
]