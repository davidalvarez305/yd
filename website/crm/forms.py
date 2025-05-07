from django import forms
import re

from core.models import Lead, LeadStatus, LeadInterest
from core.forms import BaseModelForm, BaseForm, FilterFormMixin
from core.models import MarketingCampaign, LeadMarketing, InstantForm, Cocktail, Event

class LeadForm(BaseModelForm):
    full_name = forms.CharField(
        max_length=100,
        label="Full Name*",
        widget=forms.TextInput(attrs={
            'placeholder': 'Full Name',
            'autocomplete': 'name',
            'required': True
        }),
        required=True
    )

    phone_number = forms.CharField(
        max_length=15,
        label="Phone Number*",
        widget=forms.TextInput(attrs={
            'placeholder': 'Phone Number',
            'autocomplete': 'tel-national',
            'pattern': r'^\+1\d{10}$|^\d{10}$|^\d{3}-\d{3}-\d{4}$|^\(\d{3}\) \d{3}-\d{4}$',
            'title': 'Enter a valid US phone number (e.g., +1XXXXXXXXXX, XXX-XXX-XXXX, (XXX) XXX-XXXX)',
            'required': True
        }),
        required=True
    )

    email = forms.CharField(
        max_length=255,
        label="Email",
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email',
            'autocomplete': 'email',
            'required': True
        }),
        required=False
    )

    message = forms.CharField(
        label="(OPTIONAL) Give us a few details about your event",
        widget=forms.Textarea(attrs={
            'placeholder': "It's a networking event with 50 people for 4 hours...",
            'rows': 3,
            'readonly': True
        }),
        required=False,
        disabled=True,
    )

    lead_status = forms.ModelChoiceField(
        queryset=LeadStatus.objects.all(),
        required=False,
        label="Lead Status",
        widget=forms.Select(attrs={'placeholder': 'Select a status'})
    )

    lead_interest = forms.ModelChoiceField(
        queryset=LeadInterest.objects.all(),
        required=False,
        label="Lead Interest",
        widget=forms.Select(attrs={'placeholder': 'Select interest'})
    )

    stripe_customer_id = forms.CharField(
        max_length=255,
        label="Stripe Customer ID",
        widget=forms.TextInput(attrs={
            'placeholder': 'Stripe Customer ID',
        }),
        required=False
    )

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if not re.match(r'^\+1\d{10}$|^\d{10}$|^\d{3}-\d{3}-\d{4}$|^\(\d{3}\) \d{3}-\d{4}$', phone_number):
            raise forms.ValidationError(
                'Enter a valid US phone number (e.g., +1XXXXXXXXXX, XXXXXXXXXX, XXX-XXX-XXXX, (XXX) XXX-XXXX)'
            )
        return phone_number

    class Meta:
        model = Lead
        fields = ['full_name', 'phone_number', 'email', 'lead_status', 'lead_interest', 'stripe_customer_id']

class LeadFilterForm(FilterFormMixin, BaseForm):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search for a lead...',
            'id': 'search',
            'name': 'search',
        }),
    )

    lead_interest_id = forms.ModelChoiceField(
        queryset=LeadInterest.objects.all(),
        required=False,
        empty_label="Interest",
        widget=forms.Select(attrs={
            'id': 'lead_interest_id',
            'name': 'lead_interest_id',
        })
    )

    lead_status_id = forms.ModelChoiceField(
        queryset=LeadStatus.objects.all(),
        required=False,
        empty_label="Status",
        widget=forms.Select(attrs={
            'id': 'lead_status_id',
            'name': 'lead_status_id',
        })
    )

class CocktailForm(BaseModelForm):
    name = forms.CharField(
        max_length=255,
        label="Name*",
        widget=forms.TextInput(attrs={
            'required': True
        }),
        required=True
    )

    class Meta:
        model = Cocktail
        fields = ['name']

class EventForm(BaseModelForm):
    lead = forms.ModelChoiceField(
        queryset=Lead.objects.all(),
        required=True,
        empty_label="Lead",
        widget=forms.Select(attrs={
            'id': 'lead',
            'name': 'lead',
        })
    )

    start_time = forms.DateTimeField(
        label="Start Time*",
        widget=forms.DateTimeInput(attrs={
            'required': True,
            'name': 'start_time',
            'type': 'datetime-local',
        }),
        required=True
    )

    end_time = forms.DateTimeField(
        label="End Time*",
        widget=forms.DateTimeInput(attrs={
            'required': True,
            'name': 'end_time',
            'type': 'datetime-local',
        }),
        required=True
    )

    date_paid = forms.DateTimeField(
        label="Date Paid*",
        widget=forms.DateTimeInput(attrs={
            'required': True,
            'name': 'date_paid',
            'type': 'datetime-local',
        }),
        required=True
    )

    street_address = forms.CharField(
        max_length=255,
        label="Street Address",
        widget=forms.TextInput(attrs={'name': 'street_address'}),
        required=False
    )

    city = forms.CharField(
        max_length=100,
        label="City",
        widget=forms.TextInput(attrs={'name': 'city'}),
        required=False
    )

    zip_code = forms.CharField(
        max_length=20,
        label="Zip Code",
        widget=forms.TextInput(attrs={'name': 'zip_code'}),
        required=False
    )

    amount = forms.FloatField(
        label="Amount*",
        widget=forms.NumberInput(attrs={
            'required': True,
            'name': 'amount',
        }),
        required=True
    )

    tip = forms.FloatField(
        label="Tip",
        widget=forms.NumberInput(attrs={'name': 'tip'}),
        required=False
    )

    guests = forms.IntegerField(
        label="Guests",
        widget=forms.NumberInput(attrs={'name': 'guests'}),
        required=True
    )

    class Meta:
        model = Event
        fields = [
            'start_time', 'end_time', 'date_paid', 'lead',
            'street_address', 'city', 'zip_code',
            'amount', 'tip', 'guests'
        ]

class LeadMarketingForm(BaseModelForm):
    source = forms.CharField(
        max_length=255,
        label="Source",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., Google, Facebook'
        })
    )

    medium = forms.CharField(
        max_length=255,
        label="Medium",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., CPC, email'
        })
    )

    channel = forms.CharField(
        max_length=255,
        label="Channel",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., Paid, Organic, Social'
        })
    )

    landing_page = forms.CharField(
        label="Landing Page URL",
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'https://example.com/landing-page',
            'rows': 2
        })
    )

    keyword = forms.CharField(
        max_length=255,
        label="Keyword",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., event catering nyc'
        })
    )

    referrer = forms.CharField(
        label="Referrer URL",
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'https://google.com/search?q=...',
            'rows': 2
        })
    )

    click_id = forms.CharField(
        label="Click ID",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'gclid, fbclid, etc.'
        })
    )

    client_id = forms.CharField(
        label="Client ID",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Google Analytics Client ID'
        })
    )

    button_clicked = forms.CharField(
        max_length=255,
        label="Button Clicked",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., Get a Quote, Contact Us'
        })
    )

    ip = forms.GenericIPAddressField(
        label="IP Address",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., 192.168.1.1'
        })
    )

    external_id = forms.CharField(
        label="External ID",
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'External visit or session ID',
            'required': True
        })
    )

    instant_form_lead_id = forms.IntegerField(
        label="Instant Form Lead ID",
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Meta lead form lead ID'
        })
    )

    instant_form = forms.ModelChoiceField(
        queryset=InstantForm.objects.all(),
        required=False,
        label="Instant Form",
        widget=forms.Select(attrs={
            'placeholder': 'Select Instant Form'
        })
    )

    marketing_campaign = forms.ModelChoiceField(
        queryset=MarketingCampaign.objects.all(),
        required=False,
        label="Marketing Campaign",
        widget=forms.Select(attrs={
            'placeholder': 'Select Campaign'
        })
    )

    class Meta:
        model = LeadMarketing
        fields = [
            'source', 'medium', 'channel', 'landing_page', 'keyword', 'referrer',
            'click_id', 'client_id', 'button_clicked', 'ip', 'external_id',
            'instant_form_lead_id', 'instant_form', 'marketing_campaign'
        ]