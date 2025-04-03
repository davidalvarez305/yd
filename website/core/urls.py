from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('contact', views.ContactView.as_view(), name='contact'),
    path('login', views.LoginView.as_view(), name='login'),
    path('privacy-policy', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('terms-and-conditions', views.TermsAndConditionsView.as_view(), name='terms_and_conditions'),
    path('robots.txt', views.RobotsTxtView.as_view(), name='robots_txt'),
    path('planning', views.PlanningLPView.as_view(), name='planning_lp'),
    path('staffing', views.StaffingLPView.as_view(), name='staffing_lp'),
    path('quote', views.QuoteView.as_view(), name='quote'),
    path('logout', views.LogoutView.as_view(), name='logout'),
    
    # Partial templates
    path('pop-up-modal', views.get_pop_up_modal, name='pop_up_modal'),
    path('error-modal', views.get_error_modal, name='error_modal'),
    path('opt-out-confirmation-modal', views.get_opt_out_confirmation_modal, name='opt_out_confirmation_modal'),
]