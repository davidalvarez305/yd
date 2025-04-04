from django import forms

from website.core.forms import BaseForm
from .conversions import ConversionServiceType
from http import HTTPStatus

class ConversionLogFilterForm(BaseForm):
    conversion_service_type = forms.ChoiceField(
        choices=[(item[0], item[1]) for item in ConversionServiceType.choices],
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