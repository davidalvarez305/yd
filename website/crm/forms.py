from django import forms
import re

from core.models import Lead, LeadStatus, LeadInterest
from core.forms import BaseModelForm, BaseForm, FilterFormMixin
from crm.models import Cocktail

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
        required=False
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
