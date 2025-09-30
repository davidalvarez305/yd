from django.views.generic import TemplateView, View
from django.views.generic.edit import CreateView
from django.utils import timezone
from django.http import HttpResponseServerError, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.core.files.storage import storages

from website import settings

from marketing.mixins import LandingPageMixin, UserTrackingMixin, VisitTrackingMixin
from marketing.utils import MarketingHelper
from core.email import email_service
from .logger import logger
from .models import Event, GoogleReview, Invoice, LandingPage, LandingPageConversion, Lead, LeadMarketing, LeadStatusEnum
from .utils import get_average_ratings, get_paired_reviews, is_mobile, format_phone_number, normalize_phone_number
from .forms import ContactForm, LoginForm, LeadForm
from .enums import AlertHTTPCodes, AlertStatus

class BaseView(TemplateView):
    page_title = settings.COMPANY_NAME
    meta_description = "Get a quote for mobile bartending services in Miami, FL."

    def alert(self, request, message, status: AlertStatus):
        template = 'core/success_alert.html' if status == AlertStatus.SUCCESS else 'core/error_alert.html'
        
        status_code = AlertHTTPCodes.get_http_code(status)

        return render(request, template_name=template, context={'message': message}, status=status_code)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            "page_title": self.page_title,
            "meta_description": self.meta_description,
            "site_name": settings.SITE_NAME,
            "phone_number": format_phone_number(settings.COMPANY_PHONE_NUMBER),
            "current_year": timezone.now().year,
            "company_name": settings.COMPANY_NAME,
            "page_path": f"{settings.ROOT_DOMAIN}{self.request.path}",
            "is_mobile": is_mobile(self.request.META.get('HTTP_USER_AGENT', '')),
            "media_url": settings.MEDIA_URL
        })

        return context

class BaseWebsiteView(UserTrackingMixin, VisitTrackingMixin, BaseView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        external_id = self.request.session.get('external_id')
        visit_id = self.request.session.get('visit_id')
        if external_id is None or visit_id is None:
            return HttpResponseServerError('Error retrieving external or visit ID.')

        form = LeadForm()

        context.update({
            'form': form,
            'external_id': external_id,
            'visit_id': visit_id,
            'google_analytics_id': settings.GOOGLE_ANALYTICS_ID,
            'google_ads_id': settings.GOOGLE_ADS_ID,
            'google_ads_call_conversion_label': settings.GOOGLE_ADS_CALL_CONVERSION_LABEL,
            'facebook_dataset_id': settings.FACEBOOK_DATASET_ID,
            'event_name': 'generate_lead',
            'default_currency': settings.DEFAULT_CURRENCY,
            'default_lead_value': settings.DEFAULT_LEAD_VALUE,
        })

        context['js_files'] = [
            'js/main.js',
            'js/modal/ModalHelper.js'
        ]

        return context

class HomeView(LandingPageMixin, BaseWebsiteView):
    template_name = "core/home2.html"
    page_title = f"Miami Mobile Bartending Services — {settings.COMPANY_NAME}"

    def get_template_names(self):
        default = [self.template_name]
        landing_page_id = self.request.session.get("landing_page_id")

        if not landing_page_id:
            return default

        landing_page = LandingPage.objects.filter(pk=landing_page_id).first()
        if not landing_page:
            return default

        return [f"core/landing_pages/{landing_page.template_name}"]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['js_files'] += ['js/floatingHeader.js']

        media_storage = storages['media']
        cocktail_images = [
            ('Raspberry Spritz', 'raspberry_spritz.webp'),
            ('Mojitos', 'mojitos.webp'),
            ('Mocktails', 'mocktails.webp'),
            ('Guava Margarita', 'margarita.webp'),
            ('Passionfruit Margarita', 'margarita_tower.webp'),
            ('Piña Colada', 'pina_colada.webp'),
        ]

        cocktails = [
            {
                'name': name,
                'src': media_storage.url(filename)
            }
            for name, filename in cocktail_images
        ]

        features = [
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

        faqs = [
            {
                'question': 'What types of events do you cater to?',
                'answers': [
                    "We specialize in weddings, corporate events, birthday parties, private events, festivals, and more. We can accommodate any occasion where drinks are part of the celebration!"
                ]
            },
            {
                'question': 'Do you provide the alcohol or should I supply it?',
                'answers': [
                    "We can either provide the alcohol for you or work with what you supply. We'll guide you on quantities and ensure the drinks are tailored to your preferences.",
                    "Additionally, if anything special is needed for any custom drinks, we'll be sure to let you know."
                ]
            },
            {
                'question': 'What do you charge for your service?',
                'answers': [
                    "Our pricing varies depending on the event size, location, and duration. As well, we take into accounts if you need a portable bars, supplies, glass drinkware, and other variables that will affect the final quote."
                ]
            },
            {
                'question': 'Can you create a custom cocktail menu for my event?',
                'answers': [
                    "Absolutely! Our highly skilled bartenders can design a cocktail menu that matches your event theme or your personal tastes. We also have our signature cocktails that are sure to be hits at most events."
                ]
            },
            {
                'question': 'Can you serve non-alcoholic drinks?',
                'answers': [
                    "Absolutely, we can do mocktails as well as other soft drinks & juices if requested."
                ]
            },
            {
                'question': 'Is there a minimum number of guests required?',
                'answers': [
                    "We tend to focus on events with more than 25 people, but some events have less than that and we're willing to work out a deal that is mutually beneficial."
                ]
            }
        ]

        reviews = GoogleReview.objects.all()
        paired_reviews = get_paired_reviews()
        reviews_ratings = get_average_ratings()
        events = Event.objects.count()

        signature_cocktails = [
            {
                'type': 'Signature Cocktails',
                'name': 'Spicy Mango Margarita',
                'description': 'A delectable mixture of sweet & spicy twist on a classic crowd favorite.',
                'src': 'spicy_mango_margarita.webp',
            },
            {
                'type': 'Classic Cocktails',
                'name': 'Mojito',
                'description': 'A strong case could be made that the mojito is the most popular drink in South Florida.',
                'src': 'mojitos_cocktails.webp',
            },
            {
                'type': 'Mocktails',
                'name': 'Blue Hawaiian Mocktail',
                'description': 'A sweet-n-sour, yet colorful drink — a summer classic for sure.',
                'src': 'mocktail.webp',
            },
            {
                'type': 'Beer Cocktails',
                'name': 'Michelada',
                'description': 'For those that want to take their beer to the next level with a spicy & salty mix.',
                'src': 'michelada.webp',
            },
            {
                'type': 'Frozen Cocktails',
                'name': 'Daiquiri',
                'description': 'The true summer-time special: a frozen daiquiri to cool the body down.',
                'src': 'frozen_daiquiri.webp',
            },
            {
                'type': 'Custom Drinks',
                'name': 'Passionfruit Mojito',
                'description': "If you'd like to go beyond the classics, and create your own unique blend: we can give it a go.",
                'src': 'passionfruit_mojito.webp',
            }
        ]

        left_social_images = [
            'social_proof_one.webp',
            'social_proof_two.webp',
            'social_proof_three.webp',
            'social_proof_four.webp',
        ]

        right_social_images = [
            'social_proof_five.webp',
            'social_proof_six.webp',
            'social_proof_seven.webp',
            'social_proof_eight.webp',
        ]

        offers = [
            {
                'name': 'Unwavering Attention & Care',
                'src': 'offer_one.webp',
                'description': "This is your moment, and you deserve to feel like the VIP you are. From the first pour to the final cheers, we're by your side with unmatched care.",
                'bullets': [
                    'You get our full focus—nothing less.',
                    'Your cocktails, crafted to reflect your style.',
                    "A bar setup that's as beautiful as your event.",
                    'We help you create memories that truly last.',
                ],
            },
            {
                'name': 'Artistry in Every Pour',
                'src': 'offer_two.webp',
                'description': "You don't just want drinks—you want a visual and flavorful experience. We bring flair, flavor, and a touch of magic to every cocktail we serve you.",
                'bullets': [
                    'Your cocktails become the talk of the night.',
                    'We use fresh, seasonal ingredients just for you.',
                    'Every pour looks incredible—camera-ready every time.',
                    "You'll taste (and see) the difference in every detail.",
                ],
            },
            {
                'name': 'Elevated Guest Experience',
                'src': 'offer_three.webp',
                'description': "You want your guests to feel taken care of—and we've got you. We handle the service so you can relax and enjoy your event to the fullest.",
                'bullets': [
                    'Your guests are welcomed with warmth & charm.',
                    'We keep your event flowing seamlessly behind the scenes.',
                    'You can count on professional, friendly service throughout.',
                    "You focus on fun—we've got the rest covered.",
                ],
            },
            {
                'name': 'The Aesthetic Bar Experience',
                'src': 'offer_four.webp',
                'description': "You've put so much into making your event beautiful—your bar should match that energy. We design a setup that elevates your entire vibe.",
                'bullets': [
                    'Your bar becomes a stunning visual centerpiece.',
                    'Every element—from garnishes to glassware—is styled to fit your look.',
                    "You get custom signage & menus that reflect your event's theme.",
                    "Guests won't stop snapping photos—you'll love the memories.",
                ],
            }
        ]

        comments = [f"comment_{i}.webp" for i in range(1, 14)]

        context['comments'] = comments
        context['offers'] = offers
        context['cocktails'] = cocktails
        context['features'] = features
        context['paired_reviews'] = paired_reviews
        context['reviews'] = reviews
        context['reviews_ratings'] = reviews_ratings
        context['events'] = events
        context['signature_cocktails'] = signature_cocktails
        context['left_social_images'] = left_social_images
        context['right_social_images'] = right_social_images
        context['faqs'] = faqs
        return context

class PrivacyPolicyView(BaseWebsiteView):
    template_name = "core/privacy.html"
    page_title = "Privacy Policy — " + settings.COMPANY_NAME

class TermsAndConditionsView(BaseWebsiteView):
    template_name = "core/terms.html"
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
    template_name = "core/login.html"
    page_title = f"Login — {settings.COMPANY_NAME}"

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        context['login_form'] = LoginForm()

        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect(reverse('lead_list'))

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            try:
                user = authenticate(request, username=username, password=password)

                if user is not None:
                    login(request, user)

                    redirect_url = reverse('lead_list') if request.user.is_superuser else reverse('home')

                    if self.request.headers.get("HX-Request") == "true":
                        return HttpResponse(status=200, headers={"HX-Redirect": redirect_url})

                    return redirect(redirect_url)

                else:
                    return self.alert(request, "Invalid username or password.", AlertStatus.BAD_REQUEST)
            except BaseException as e:
                return self.alert(request, "Internal server error.", AlertStatus.INTERNAL_ERROR)
        else:
            return self.alert(request, "Invalid form submission.", AlertStatus.BAD_REQUEST)

class ContactView(BaseWebsiteView):
    template_name = 'core/contact_form.html'
    page_title = 'Contact - ' + settings.COMPANY_NAME

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        context['contact_form'] = ContactForm()
        return render(request, self.template_name, context=context)

    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST)
        
        if form.is_valid():
            try:
                form.send_email()
                return self.alert(request, "Contact form received successfully.", AlertStatus.SUCCESS)
            except Exception as e:
                logger.exception(str(e))
                return self.alert(request, "Failed to send the contact form.", AlertStatus.BAD_REQUEST)
        else:
            return self.alert(request, "Invalid form data.", AlertStatus.BAD_REQUEST)

class LogoutView(BaseWebsiteView):
    def post(self, request, *args, **kwargs):
        logout(request)
        return redirect(reverse('home'))

class LeadCreateView(BaseView, CreateView):
    model = Lead
    form_class = LeadForm

    def form_valid(self, form):
        try:
            with transaction.atomic():
                lead = form.save()

                if self.request.user.is_authenticated:
                    lead_marketing = LeadMarketing.objects.create(lead=lead)
                else:
                    marketing_helper = MarketingHelper(self.request)
                    lead_marketing = LeadMarketing.objects.create(
                        lead=lead,
                        ip=marketing_helper.ip,
                        external_id=marketing_helper.external_id,
                        user_agent=marketing_helper.user_agent,
                        ad=marketing_helper.ad,
                    )
                    marketing_helper.save_metadata(lead_marketing=lead_marketing)

                    lp = self.request.session.get("landing_page_id")
                    if lp:
                        landing_page = LandingPage.objects.filter(pk=lp).first()
                        if landing_page:
                            conversion = LandingPageConversion(
                                lead=lead,
                                landing_page=landing_page,
                            )
                            conversion.save()

                lead.change_lead_status(status=LeadStatusEnum.LEAD_CREATED)

            return self.alert(self.request, "Your request was successfully submitted!", AlertStatus.SUCCESS)

        except Exception as e:
            logger.exception(str(e))
            return self.alert(self.request, "Internal server error", AlertStatus.INTERNAL_ERROR)

    def form_invalid(self, form):
        phone_errors = form.errors.get('phone_number')
        if phone_errors and any('already submitted' in error for error in phone_errors):

            phone_number = normalize_phone_number(form.data.get('phone_number'))
            lead = Lead.objects.filter(phone_number=phone_number).first()

            if not lead:
                return self.alert(self.request, 'Error while querying lead.', AlertStatus.INTERNAL_ERROR)
            
            try:
                lead_details = settings.ROOT_DOMAIN + reverse("lead_detail", kwargs={ 'pk': lead.pk })
                
                html = f"""
                    <html>
                    <body>
                        <p><a href="{lead_details}">View lead</a></p>
                    </body>
                    </html>
                """
                
                email_service.send_html_email(
                    to=settings.COMPANY_EMAIL,
                    subject=f'{lead.full_name} CAME BACK',
                    html=html
                )
            except Exception as e:
                logger.exception(str(e), exc_info=True)
            
            return self.alert(self.request, f"Welcome back {lead.full_name}, we'll be in touch soon!", AlertStatus.BAD_REQUEST)

        errors = '\n'.join([f"{', '.join(errors)}" for _, errors in form.errors.items()])
        return self.alert(self.request, errors, AlertStatus.BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        self.request = request
        return super().post(request, *args, **kwargs)
    
class SuccessPaymentView(BaseWebsiteView):
    template_name = "core/thank_you.html"
    page_title = "Thank You — " + settings.COMPANY_NAME
    model = Invoice
    context_object_name = 'invoice'

    def get_object(self, queryset=None):
        external_id = self.kwargs.get('external_id')
        return get_object_or_404(Invoice, external_id=external_id)

def redirect_external(request, external_id):
    return redirect(reverse('external_quote_view', kwargs={'external_id': external_id}))

class ChairRentals(BaseWebsiteView):
    template_name = "core/landing_pages/chair_rentals.html"
    page_title = f"Chair Rentals Miami — {settings.COMPANY_NAME}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['js_files'] += ['js/floatingHeader.js']

        reviews = GoogleReview.objects.all()
        paired_reviews = get_paired_reviews()
        reviews_ratings = get_average_ratings()
        events = Event.objects.count()

        media_storage = storages['media']
        # 'image': media_storage.url('spicy_mango_margarita.webp'),

        items = [
            {
                'name': 'Plastic Folding Chairs',
                'price': 2.00,
                'image': 'https://chiavarisales.com/cdn/shop/files/CFPW-AX-T.jpg?v=1757976350&width=1600',
            },
            {
                'name': 'Resin Folding Chairs',
                'price': 4.00,
                'image': 'https://chiavarisales.com/cdn/shop/files/CFRW-CX-T-1.jpg?v=1758113383&width=1600',
            },
            {
                'name': 'Chiavari Chairs',
                'price': 7.00,
                'image': 'https://chiavarisales.com/cdn/shop/files/Gold-Resin-Steel-Skeleton_1-1_de46bb55-adf0-4df6-9a1f-b9d8f94ee58b.jpg?v=1747389562&width=1600',
            },
            {
                'name': 'Cross Back Chairs',
                'price': 10.00,
                'image': 'https://chiavarisales.com/cdn/shop/files/crossback-resin-chestnut_1_7c9b311d-ec08-44e4-8ef3-cbefdfed349b.jpg?v=1757595775&width=1600',
            },
            {
                'name': 'Royal Chairs',
                'price': 15.00,
                'image': 'https://chiavarisales.com/cdn/shop/files/Royal-Resin-Gold-with-Ivory-Vinyl-Seat-and-Ivory-Vinyl-Tufted-Back_1-scaled.jpg?v=1747364239&width=1600',
            },
            {
                'name': 'Bamboo Chairs',
                'price': 10.00,
                'image': 'https://chiavarisales.com/cdn/shop/files/bamboo_steel_skeleton_chair_01.jpg?v=1757602482&width=1600',
            },
            {
                'name': 'O Chairs',
                'price': 15.00,
                'image': 'https://chiavarisales.com/cdn/shop/files/OChairGoldStainlessSteel_1.jpg?v=1747377300&width=1600',
            },
            {
                'name': 'Bar Stools',
                'price': 15.00,
                'image': 'https://chiavarisales.com/cdn/shop/files/bcrg-st-ax-t2.jpg?v=1757602551&width=1600',
            },
        ]

        faqs = [
            {
                'question': 'What types of events do you cater to?',
                'answers': [
                    "We specialize in weddings, corporate events, birthday parties, private events, festivals, and more. It doesn't matter if it's an event venue, a backyard party, an office building — we've got you covered."
                ]
            },
            {
                'question': 'Do you provide delivery & set-up or just pick-up?',
                'answers': [
                    "You can do whichever of the three options: delivery only, delivery + set-up, or pick-up. Whatever makes the most sense for you works for us, as well."
                ]
            },
            {
                'question': 'What do you charge for your service?',
                'answers': [
                    "Once we've received some basic details from you, we'll provide with you a highly detailed & itemized invoice that will contain all the information you need about your rental services. Including chairs, delivery, set-up, any add-on's such as covers or cushions, etc..."
                ]
            },
            {
                'question': 'Do you offer delivery and setup for your chairs?',
                'answers': [
                    "Yes, we provide both delivery and setup services for all chair rentals. In the event that you do want it, delivery fees are dependent on distance & set-up is dependent on estimated labor hours."
                ]
            },
            {
                'question': 'What types of chairs do you offer for different events?',
                'answers': [
                    "More than just the ones pictured on the website, we can meet your needs with whatever style and/or material you might desire for your party."
                ]
            },
            {
                'question': 'How far in advance should I book my chair rentals?',
                'answers': [
                    "We recommend booking your chair rentals at least 2-4 weeks in advance to ensure availability, especially during peak event seasons."
                    "However, we do our best to accommodate last-minute requests if needed, so feel free to contact us, and we’ll work with your timeline!"
                ]
            }
        ]

        features = [
            "We’ll help you pick out the perfect chairs that fit your event’s vibe—whether it’s casual, classy, or somewhere in between.",
            "We’re always early to set up—sometimes even hours before your event starts—so everything’s ready and waiting for your guests to arrive.",
            "Our chairs are not just stylish, but also kept in top condition. They’re cleaned thoroughly and stored neatly after each event, ensuring they're fresh and sanitized for your big day.",
            "We’re all about cleanliness—your event space will be spotless when we leave, and we’ll take care of the cleanup so you don’t have to worry about a thing.",
            "Need the chairs to match a dress code or theme? We’ve got you covered—we can set up everything to fit your style, while keeping everything neat and organized.",
            "Big event or small, we’ve got the seating you need to make sure everyone’s comfortable and everything looks perfect.",
            "We’ll give you a straightforward, customized quote so you know exactly what you’re paying for—no surprises, just great service.",
            "Your guests’ comfort is our number one priority—we’ll make sure every chair is spotless and ready to go before anyone sits down.",
            "With years of experience, we’re proud to offer timely, reliable service that makes your event setup smooth and stress-free."
        ]

        comments = [f"comment_{i}.webp" for i in range(1, 14)]

        context['paired_reviews'] = paired_reviews
        context['reviews'] = reviews
        context['reviews_ratings'] = reviews_ratings
        context['events'] = events
        context['items'] = items
        context['faqs'] = faqs
        context['comments'] = comments
        context['features'] = features
        return context