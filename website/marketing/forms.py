from django import forms

from core.forms import BaseForm
from marketing.enums import CONVERSION_SERVICE_CHOICES
from .conversions import ConversionServiceType
from .models import MarketingCampaign, CallTrackingNumber
from http import HTTPStatus

class CallTrackingNumberForm(BaseForm):
    class Meta:
        model = CallTrackingNumber
        fields = ['platform_id', 'call_tracking_number', 'campaign']

class ConversionLogFilterForm(BaseForm):
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