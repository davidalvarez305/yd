from django import forms

from core.models import Message, PhoneCall
from core.forms import BaseModelForm, MultiFileInput, MultiMediaFileField

class MessageForm(BaseModelForm):
    text = forms.CharField(
        label="Message*",
        widget=forms.Textarea(attrs={'rows': 3, 'required': False}),
        required=False
    )

    message_media = MultiMediaFileField(
        widget=MultiFileInput(attrs={
            'multiple': True,
            'style': 'display: none;',
            'id': 'messageMedia',
            'accept': 'audio/*, image/*, video/*'
        }),
        required=False,
        field_name='messageMedia',
    )

    text_to = forms.CharField(widget=forms.HiddenInput())
    text_from = forms.CharField(widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()
        text = cleaned_data.get('text')
        message_media = cleaned_data.get('message_media')

        if not text and not message_media:
            raise forms.ValidationError("Either a text or media file must be provided.")

        return cleaned_data

    class Meta:
        model = Message
        fields = ['text', 'message_media', 'text_to', 'text_from']

class PhoneCallForm(BaseModelForm):
    is_inbound = forms.BooleanField(
        widget=forms.CheckboxInput(
            attrs={ 'disabled': True }),
            label = 'Inbound'
        )

    class Meta:
        model = PhoneCall
        fields = '__all__'

class OutboundPhoneCallForm(forms.Form):
    to_ = forms.CharField(widget=forms.HiddenInput())
    from_ = forms.CharField(widget=forms.HiddenInput())