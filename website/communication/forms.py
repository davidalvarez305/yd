from django import forms

from .models import Message
from core.forms import BaseModelForm

class MessageForm(BaseModelForm):
    message = forms.CharField(
        label="Message*",
        widget=forms.Textarea(attrs={'rows': 3, 'required': True}),
        required=True
    )

    message_media = forms.FileField(
        label="Media (optional)",
        widget=forms.ClearableFileInput(attrs={'multiple': True}),
        required=False
    )

    class Meta:
        model = Message
        fields = ['message', 'message_media']