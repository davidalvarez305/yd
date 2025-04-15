from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import re

from core.widgets import ToggleSwitchWidget

class BaseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.NumberInput):
                field.widget.attrs.update({
                    'class': 'block w-full rounded-lg border border-gray-200 px-5 py-3 leading-6 placeholder-gray-500 focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:placeholder-gray-400 dark:focus:border-primary'
                })
            elif isinstance(field.widget, forms.TextInput):
                field.widget.attrs.update({
                    'class': 'block w-full rounded-lg border border-gray-200 px-5 py-3 leading-6 placeholder-gray-500 focus:border-primary-500 focus:ring focus:ring-primary-500/50 dark:border-gray-600 dark:bg-gray-800 dark:placeholder-gray-400 dark:focus:border-primary-500'
                })
            elif isinstance(field.widget, forms.EmailInput):
                field.widget.attrs.update({
                    'class': 'block w-full rounded-lg border border-gray-200 px-5 py-3 leading-6 placeholder-gray-500 focus:border-primary-500 focus:ring focus:ring-primary-500/50 dark:border-gray-600 dark:bg-gray-800 dark:placeholder-gray-400 dark:focus:border-primary-500'
                })
            elif isinstance(field.widget, forms.PasswordInput):
                field.widget.attrs.update({
                    'class': 'block w-full rounded-lg border border-gray-200 px-5 py-3 leading-6 placeholder-gray-500 focus:border-primary-500 focus:ring focus:ring-primary-500/50 dark:border-gray-600 dark:bg-gray-800 dark:placeholder-gray-400 dark:focus:border-primary-500'
                })
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({
                    'class': 'block w-full rounded-lg border border-gray-200 px-5 py-3 leading-6 placeholder-gray-500 focus:border-primary-500 focus:ring focus:ring-primary-500/50 dark:border-gray-600 dark:bg-gray-800 dark:placeholder-gray-400 dark:focus:border-primary-500'
                })
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'block w-full rounded-lg border border-gray-200 px-5 py-3 leading-6 focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:focus:border-primary'
                })
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'peer sr-only'
                })
            if field.label:
                field.widget.attrs['class'] = (field.widget.attrs.get('class', '') + ' font-medium').strip()

    def as_div(self):
        """
        Return the form fields wrapped in divs with Tailwind CSS classes.
        """
        form_html = ''
        for field_name, field in self.fields.items():
            field_id = field.widget.attrs.get('id', field_name)
            
            field_html = field.widget.render(field_name, field.initial)

            # Skip external label if widget handles its own label
            if isinstance(field.widget, ToggleSwitchWidget):
                label = ''
            else:
                label = f'<label for="{field_id}" class="font-medium">{field.label}</label>'

            field_div = f'<div class="space-y-1">{label}{field_html}</div>'
            form_html += field_div
        return form_html

class LoginForm(BaseForm):
    username = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Username...',
            'required': True
        }),
        required=True
    )
    password = forms.CharField(
        max_length=100,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password...',
            'required': True
        }),
        required=True)

    def clean_username(self):
        username = self.cleaned_data.get('username')
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise ValidationError("Username does not exist.")
        return username

class ContactForm(BaseForm):
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'First Name',
            'required': True
        }),
        required=True
    )
    
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Last Name',
            'required': True
        }),
        required=True
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email',
            'required': True
        }),
        required=True
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Your Message...',
            'rows': 6,
            'required': True
        }),
        required=True
    )

class QuoteForm(BaseForm):
    full_name = forms.CharField(
        max_length=100,
        label="Full Name*",
        widget=forms.TextInput(attrs={
            'placeholder': 'Full Name',
            'autocomplete': 'name',
            'required': True,
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
            'required': True,
        }),
        required=True
    )

    message = forms.CharField(
        label="(OPTIONAL) Give us a few details about your event",
        widget=forms.Textarea(attrs={
            'placeholder': "It's a networking event with 50 people for 4 hours...",
            'rows': 3,
        }),
        required=False
    )

    opt_in_text_messaging = forms.BooleanField(
        required=False,
        initial=True,
        widget=ToggleSwitchWidget(attrs={
            'id': 'opt_in_text_messaging',
        }),
    )

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if not re.match(r'^\+1\d{10}$|^\d{3}[-]?\d{3}[-]?\d{4}$|^\(\d{3}\) \d{3}[-]?\d{4}$', phone_number):
            raise forms.ValidationError('Enter a valid US phone number (e.g., +1XXXXXXXXXX, XXXXXXXXXX, XXX-XXX-XXXX, (XXX) XXX-XXXX)')
        return phone_number