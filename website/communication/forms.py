from django import forms

from .models import Message
from core.forms import BaseModelForm, MultiFileField, MultiFileInput

class MessageForm(BaseModelForm):
    message = forms.CharField(
        label="Message*",
        widget=forms.Textarea(attrs={'rows': 3, 'required': True}),
        required=True
    )

    message_media = MultiFileField(
        label="Media (optional)",
        widget=MultiFileInput(attrs={'multiple': True}),
        required=False
    )

    text_to = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = Message
        fields = ['message', 'message_media']