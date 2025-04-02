from django.urls import path
from .views import (
    HomeView,
    ContactView,
    LoginView,
    PrivacyPolicyView,
    TermsAndConditionsView,
    RobotsTxtView,
    PlanningLPView,
    StaffingLPView,
    QuoteView,
    LogoutView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('contact', ContactView.as_view(), name='contact'),
    path('login', LoginView.as_view(), name='login'),
    path('privacy-policy', PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('terms-and-conditions', TermsAndConditionsView.as_view(), name='terms_and_conditions'),
    path('robots.txt', RobotsTxtView.as_view(), name='robots_txt'),
    path('planning', PlanningLPView.as_view(), name='planning_lp'),
    path('staffing', StaffingLPView.as_view(), name='staffing_lp'),
    path('quote', QuoteView.as_view(), name='quote'),
    path('logout', LogoutView.as_view(), name='logout'),
]