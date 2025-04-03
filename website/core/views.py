from django.views.generic import TemplateView, View
from django.utils.timezone import now
from django.http import HttpResponseServerError, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from website.communication.email import get_email_service
from website.website import settings

from .forms import ContactForm, LoginForm, QuoteForm

class BaseView(TemplateView):
    page_title = settings.COMPANY_NAME
    meta_description = "Get a quote for mobile bartending services in Miami, FL."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            "page_title": self.page_title,
            "meta_description": self.meta_description,
            "site_name": settings.SITE_NAME,
            "phone_number": settings.COMPANY_PHONE_NUMBER,
            "current_year": now().year,
            "company_name": settings.COMPANY_NAME,
            "page_path": f"{settings.ROOT_DOMAIN}{self.request.path}",
        })

        return context


class BaseWebsiteView(BaseView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # External ID check
        external_id = self.request.session.get("external_id")
        if external_id is None:
            return HttpResponseServerError("Error retrieving external ID.")

        # Add additional website-specific context
        context.update({
            "external_id": external_id,
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
            "is_mobile": self.request.user_agent.is_mobile if hasattr(self.request, 'user_agent') else False,
        })

        return context

class HomeView(BaseWebsiteView):
    template_name = "home.html"
    page_title = f"Miami Mobile Bartending Services — {settings.COMPANY_NAME}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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

class PlanningLPView(BaseWebsiteView):
    template_name = "planning_lp.html"
    page_title = f"Miami Party Planning Service — {settings.COMPANY_NAME}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["features"] = [
            "We design custom event plans including themed décor, catering, and entertainment.",
            "Our team arrives early to ensure everything is set up perfectly.",
            "We uphold the highest service standards for a seamless guest experience.",
            "We offer a list of vetted vendors to bring your vision to life.",
            "Our staff can match your event’s theme for a cohesive atmosphere.",
            "We cater to both small and large events efficiently.",
            "We provide clear, transparent quotes with no hidden fees.",
            "Your guests’ experience is our priority—we create unforgettable events.",
            "Our team brings creativity and expertise to every event.",
        ]
        return context

class StaffingLPView(BaseWebsiteView):
    template_name = "staffing_lp.html"
    page_title = f"Miami Event Staff for Hire — {settings.COMPANY_NAME}"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["features"] = [
            "We bring your event vision to life, whether it’s the vibe, the crew, or the full setup.",
            "Our team arrives early to handle setup and ensure everything runs smoothly.",
            "We provide top-tier service, making sure your guests feel taken care of.",
            "We connect you with trusted vendors for food, décor, and entertainment.",
            "Our staff can dress to match your event theme for a seamless look.",
            "We can accommodate both small and large gatherings.",
            "Our pricing is clear and upfront, ensuring no surprises.",
            "Your guests’ experience is our top priority, ensuring an unforgettable event.",
            "Our team consists of experienced professionals bringing creativity and expertise.",
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
        context['form'] = LoginForm()

        # Check if the user is already logged in
        if request.user.is_authenticated:
            if request.request.user.is_superuser:
                messages.info(request, "Already logged in.")
                return redirect(reverse('crm_leads'))

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            # Authenticate the user
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)

                if request.user.is_superuser:
                    return redirect(reverse('crm_leads'))

                # Normal user redirection
                return redirect(reverse('home'))
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid form submission.")

        return render(request, self.template_name, { 'form': form })

class ContactView(BaseWebsiteView):
    template_name = 'contact.html'
    page_title = 'Contact - ' + settings.COMPANY_NAME

    def get(self, request, *args, **kwargs):
        form = ContactForm()
        return render(request, self.template_name, { 'form': form })

    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST)
        
        if form.is_valid():
            try:
                email_service = get_email_service()
                email_service.send_email(
                    to=form.cleaned_data["email"],
                    subject="YD Cocktails: Contact Form Submission",
                    body=form.cleaned_data["message"]
                )
                messages.success(request, "Contact form received successfully.")
                return redirect(reverse('contact'))
            except Exception as e:
                messages.error(request, "Failed to send the contact form.")
                return redirect(reverse('contact'))
        else:
            messages.error(request, "Invalid form data.")
            return render(request, self.template_name, {
                'form': form,
                'page_title': self.page_title,
            })

class LogoutView(BaseWebsiteView):
    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect(reverse('home'))