from django import forms
import re

from core.models import Lead, LeadStatus, LeadInterest
from core.forms import BaseModelForm, BaseForm

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
        max_length=15,
        label="Email",
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email',
            'autocomplete': 'email',
            'required': True
        }),
        required=True
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

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if not re.match(r'^\+1\d{10}$|^\d{10}$|^\d{3}-\d{3}-\d{4}$|^\(\d{3}\) \d{3}-\d{4}$', phone_number):
            raise forms.ValidationError(
                'Enter a valid US phone number (e.g., +1XXXXXXXXXX, XXXXXXXXXX, XXX-XXX-XXXX, (XXX) XXX-XXXX)'
            )
        return phone_number

    class Meta:
        model = Lead
        fields = ['full_name', 'phone_number', 'email', 'lead_status', 'lead_interest']

class LeadFilterForm(BaseForm):
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

class VisitFilterForm(forms.Form):
    referrer = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by Referrer...',
            'id': 'referrer',
            'name': 'referrer',
        })
    )

    url = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by URL...',
            'id': 'url',
            'name': 'url',
        })
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'placeholder': 'Start Date (YYYY-MM-DD)',
            'id': 'date_from',
            'name': 'date_from',
            'type': 'date',
        })
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'placeholder': 'End Date (YYYY-MM-DD)',
            'id': 'date_to',
            'name': 'date_to',
            'type': 'date',
        })
    )

    session_duration_min = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Min Duration (seconds)',
            'id': 'session_duration_min',
            'name': 'session_duration_min',
        })
    )

    session_duration_max = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Max Duration (seconds)',
            'id': 'session_duration_max',
            'name': 'session_duration_max',
        })
    )

    lead = forms.ModelChoiceField(
        queryset=Lead.objects.all(),
        required=False,
        empty_label="Select Lead",
        widget=forms.Select(attrs={
            'id': 'lead',
            'name': 'lead',
        })
    )

    def filter_queryset(self, queryset):
        if self.cleaned_data.get('referrer'):
            queryset = queryset.filter(referrer__icontains=self.cleaned_data['referrer'])

        if self.cleaned_data.get('url'):
            queryset = queryset.filter(url__icontains=self.cleaned_data['url'])

        if self.cleaned_data.get('date_from'):
            queryset = queryset.filter(date_created__gte=self.cleaned_data['date_from'])

        if self.cleaned_data.get('date_to'):
            queryset = queryset.filter(date_created__lte=self.cleaned_data['date_to'])

        if self.cleaned_data.get('session_duration_min') is not None:
            queryset = queryset.filter(session_duration__gte=self.cleaned_data['session_duration_min'])

        if self.cleaned_data.get('session_duration_max') is not None:
            queryset = queryset.filter(session_duration__lte=self.cleaned_data['session_duration_max'])

        if self.cleaned_data.get('lead'):
            queryset = queryset.filter(lead=self.cleaned_data['lead'])

        return queryset