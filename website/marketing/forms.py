from django import forms

from core.forms import BaseForm, BaseModelForm, FilterFormMixin
from core.models import Lead
from marketing.enums import ConversionServiceType
from core.models import MarketingCampaign, CallTrackingNumber
from .models import Visit
from http import HTTPStatus

class CallTrackingNumberForm(BaseModelForm):
    marketing_campaign = forms.ModelChoiceField(
        queryset=MarketingCampaign.objects.all(),
        required=True,
        empty_label='---',
        label='Marketing Campaign',
    )

    class Meta:
        model = CallTrackingNumber
        fields = ['call_tracking_number']

class HTTPLogFilterForm(FilterFormMixin, BaseForm):
    status_code = forms.ChoiceField(
        choices=[(str(status.value), status.name) for status in HTTPStatus],
        required=False,
        label='Status Code'
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

class VisitFilterForm(FilterFormMixin, BaseForm):
    referrer = forms.CharField(
        label='Referrer',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by Referrer...',
            'id': 'referrer',
            'name': 'referrer',
        })
    )

    url = forms.CharField(
        label='LP',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by URL...',
            'id': 'url',
            'name': 'url',
        })
    )

    date_from = forms.DateField(
        label='Date From',
        required=False,
        widget=forms.DateInput(attrs={
            'placeholder': 'Start Date (YYYY-MM-DD)',
            'id': 'date_from',
            'name': 'date_from',
            'type': 'date',
        })
    )

    date_to = forms.DateField(
        label='Date To',
        required=False,
        widget=forms.DateInput(attrs={
            'placeholder': 'End Date (YYYY-MM-DD)',
            'id': 'date_to',
            'name': 'date_to',
            'type': 'date',
        })
    )
    
    lead = forms.ModelChoiceField(
        queryset=Lead.objects.all(),
        required=False,
        empty_label="Select Lead",
        label='Lead',
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