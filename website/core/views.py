from django.views.generic import TemplateView, View
from django.utils.timezone import now
from django.http import HttpResponseServerError, HttpResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout

from website import settings

from .utils import is_mobile, format_phone_number
from .forms import ContactForm, LoginForm, QuoteForm
from .models import Lead
from .enums import AlertStatus
from communication.email import get_email_service

class BaseView(TemplateView):
    page_title = settings.COMPANY_NAME
    meta_description = "Get a quote for mobile bartending services in Miami, FL."

    def alert(self, request, message, status: AlertStatus):
        template = 'core/success_alert.html' if status == AlertStatus.SUCCESS else 'core/error_alert.html'
        
        status_code = { AlertStatus.SUCCESS: 200, AlertStatus.BAD_REQUEST: 400, AlertStatus.INTERNAL_ERROR: 500 }.get(status, 500)

        return render(request, template_name=template, context={'message': message}, status=status_code)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            "page_title": self.page_title,
            "meta_description": self.meta_description,
            "site_name": settings.SITE_NAME,
            "phone_number": format_phone_number(settings.COMPANY_PHONE_NUMBER),
            "current_year": now().year,
            "company_name": settings.COMPANY_NAME,
            "page_path": f"{settings.ROOT_DOMAIN}{self.request.path}",
            "is_mobile": is_mobile(self.request.META.get('HTTP_USER_AGENT', '')),
        })

        return context


class BaseWebsiteView(BaseView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        external_id = self.request.session.get("external_id")
        visit_id = self.request.session.get("visit_id")
        if external_id is None or visit_id is None:
            return HttpResponseServerError("Error retrieving external or visit ID.")
        
        form = QuoteForm()

        context.update({
            "quote_form": form,
            "external_id": external_id,
            "visit_id": visit_id,
            "google_analytics_id": settings.GOOGLE_ANALYTICS_ID,
            "google_ads_id": settings.GOOGLE_ADS_ID,
            "google_ads_call_conversion_label": settings.GOOGLE_ADS_CALL_CONVERSION_LABEL,
            "facebook_dataset_id": settings.FACEBOOK_DATASET_ID,
            "lead_event_name": settings.LEAD_EVENT_NAME,
            "lead_generated_event_name": settings.LEAD_GENERATED_EVENT_NAME,
            "default_currency": settings.DEFAULT_CURRENCY,
            "default_lead_value": settings.DEFAULT_LEAD_VALUE,
            "yova_hero_image": "https://ydcocktails.s3.us-east-1.amazonaws.com/media/yova_hero.jpeg",
            "yova_most_popular_package": "https://ydcocktails.s3.us-east-1.amazonaws.com/media/yova_mid_cta.png",
            "yova_basic_package": "https://ydcocktails.s3.us-east-1.amazonaws.com/media/yova_basic_package.jpeg",
            "yova_open_bar_package": "https://ydcocktails.s3.us-east-1.amazonaws.com/media/yova_open_bar_package.jpeg",
        })

        context['js_files'] = [
            'js/main.js',
            'js/modal.js'
        ]

        return context

class HomeView(BaseWebsiteView):
    template_name = "core/home.html"
    page_title = f"Miami Mobile Bartending Services — {settings.COMPANY_NAME}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['js_files'] += ['js/floatingHeader.js']

        context["features"] = [
            "We'll work with you to create a custom menu that features our signature cocktails + your favorites.",
            "We'll always be early to setup & make sure everything that's necessary is ready for use.",
            "We have high standards of service to make sure your guests enjoy their time with cold & delicious drinks.",
            "We will clean up after ourselves and leave your area as clean as it was before we got there.",
            "Our team can dress to the occasion if a specific outfit or theme is required.",
            "We offer flexible capacity, serving both small and large events.",
            "We provide detailed & customized quotes so you know exactly what you're paying for.",
            "Your guests are our priority, ensuring an incredible service and experience.",
            "Our bartenders are highly skilled with years of experience, making top-tier cocktails.",
        ]
        return context

class PrivacyPolicyView(BaseWebsiteView):
    template_name = "privacy.html"
    page_title = "Privacy Policy — " + settings.COMPANY_NAME

class TermsAndConditionsView(BaseWebsiteView):
    template_name = "terms.html"
    page_title = "Terms & Conditions — " + settings.COMPANY_NAME

class RobotsTxtView(View):
    def get(self, request, *args, **kwargs):
        robots_txt_content = """\
        # robots.txt for https://ydcocktails.com/

        # Allow all robots complete access
        User-agent: *
        Disallow:
        """
        return HttpResponse(robots_txt_content, content_type="text/plain")

class LoginView(BaseWebsiteView):
    template_name = "login.html"
    page_title = f"Login — {settings.COMPANY_NAME}"

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        context['login_form'] = LoginForm()

        if request.user.is_authenticated:
            if request.request.user.is_superuser:
                return redirect(reverse('crm_leads'))

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)

                if request.user.is_superuser:
                    return redirect(reverse('crm_leads'))

                return redirect(reverse('home'))
            else:
                return self.alert(request, "Invalid username or password.", AlertStatus.BAD_REQUEST)
        else:
            return self.alert(request, "Invalid form submission.", AlertStatus.BAD_REQUEST)

class ContactView(BaseWebsiteView):
    template_name = 'contact.html'
    page_title = 'Contact - ' + settings.COMPANY_NAME

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, { 'contact_form': ContactForm() })

    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST)
        
        if form.is_valid():
            try:
                form.send_email(email_service=get_email_service())
                return self.alert(request, "Contact form received successfully.", AlertStatus.SUCCESS)
            except Exception as e:
                return self.alert(request, "Failed to send the contact form.", AlertStatus.BAD_REQUEST)
        else:
            return self.alert(request, "Invalid form data.", AlertStatus.BAD_REQUEST)

class LogoutView(BaseWebsiteView):
    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect(reverse('home'))

class QuoteView(BaseWebsiteView):
    def post(self, request, *args, **kwargs):
        form = QuoteForm(request.POST)

        if form.is_valid():
            try:
                cleaned_phone_number = form.cleaned_data['phone_number']
            
                if Lead.objects.filter(phone_number=cleaned_phone_number).exists():
                    return self.alert(request, "We already have this info saved", AlertStatus.BAD_REQUEST)
                
                form.save()

                return self.alert(request, "Your request was successfully submitted!", AlertStatus.SUCCESS)
            except Exception as e:
                return self.alert(request, "Internal server error", AlertStatus.INTERNAL_ERROR)
        else:
            return self.alert(request, "Form fields incorrectly submitted.", AlertStatus.BAD_REQUEST)