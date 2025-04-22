from django import forms

from .models import Message
from core.forms import BaseModelForm, MultiFileField, MultiFileInput

class MessageForm(BaseModelForm):
    message = forms.CharField(
        label="Message*",
        widget=forms.Textarea(attrs={'rows': 3, 'required': False}),
        required=False
    )

    message_media = MultiFileField(
        widget=MultiFileInput(attrs={
            'multiple': True,
            'style': 'display: none;',
            'id': 'messageMedia',
            'accept': 'audio/*, image/*, video/*'
        }),
        required=False
    )

    text_to = forms.CharField(widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = super().clean()
        message = cleaned_data.get('message')
        message_media = cleaned_data.get('message_media')

        if not message and not message_media:
            raise forms.ValidationError("Either a message or media file must be provided.")

        return cleaned_data

    class Meta:
        model = Message
        fields = ['message', 'message_media']