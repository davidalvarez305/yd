from django import forms

from core.forms import BaseForm, BaseModelForm
from core.models import Lead
from marketing.enums import CONVERSION_SERVICE_CHOICES
from .conversions import ConversionServiceType
from .models import MarketingCampaign, CallTrackingNumber, Visit
from http import HTTPStatus

class CallTrackingNumberForm(BaseModelForm):
    class Meta:
        model = CallTrackingNumber
        fields = ['platform_id', 'call_tracking_number', 'marketing_campaign']

class ConversionLogFilterForm(BaseModelForm):
    conversion_service_type = forms.ChoiceField(
        choices=CONVERSION_SERVICE_CHOICES,
        required=False,
        label='Conversion Service'
    )
    status_code = forms.ChoiceField(
        choices=[(str(status.value), status.name) for status in HTTPStatus],
        required=False,
        label='Status Code'
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['conversion_service_type'].empty_label = "All Types"
        self.fields['status_code'].empty_label = "All Statuses"

class CallTrackingFilterForm(BaseForm):
    conversion_service_type = forms.ChoiceField(
        choices=[('', 'All Types')] + [(item.value, item.name.title()) for item in ConversionServiceType],
        required=False,
        label='Ad Platform',
    )
    campaign = forms.ModelChoiceField(
        queryset=MarketingCampaign.objects.all(),
        required=False,
        empty_label='All',
        label='Campaign',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class VisitForm(BaseModelForm):
    class Meta:
        model = Visit
        fields = ['session_duration']

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