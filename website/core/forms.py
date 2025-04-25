from django import forms
from django.core.exceptions import ValidationError
import re

from core.utils import add_form_field_class
from core.widgets import ToggleSwitchWidget
from core.models import Lead, Service, UnitType, User, ServiceType
from communication.email import EmailService
from website.settings import COMPANY_NAME

class MultiFileInput(forms.FileInput):
    allow_multiple_selected = True

class MultiFileField(forms.FileField):
    widget = MultiFileInput

    def clean(self, data, initial=None):
        files = data or []
        if self.required and not files:
            raise forms.ValidationError(self.error_messages['required'], code='required')
        return files

class StyledFormMixin:
    def apply_styling(self):
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.NumberInput):
                add_form_field_class(widget, 'block w-full rounded-lg border border-gray-200 px-5 py-3 leading-6 placeholder-gray-500 focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:placeholder-gray-400 dark:focus:border-primary')
            elif isinstance(widget, (forms.TextInput, forms.EmailInput, forms.PasswordInput, forms.Textarea)):
                add_form_field_class(widget, 'block w-full rounded-lg border border-gray-200 px-5 py-3 leading-6 placeholder-gray-500 focus:border-primary-500 focus:ring focus:ring-primary-500/50 dark:border-gray-600 dark:bg-gray-800 dark:placeholder-gray-400 dark:focus:border-primary-500')
            elif isinstance(widget, forms.Select):
                add_form_field_class(widget, 'block w-full rounded-lg border border-gray-200 px-5 py-3 leading-6 focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50 dark:border-gray-600 dark:bg-gray-800 dark:focus:border-primary')
            elif isinstance(widget, forms.CheckboxInput):
                add_form_field_class(widget, 'peer sr-only')
            add_form_field_class(widget, 'font-medium')

class FilterFormMixin:
    def apply_styling(self):
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.TextInput, forms.EmailInput, forms.PasswordInput, forms.Textarea)):
                add_form_field_class(widget, 'block w-full rounded-lg border border-gray-200 py-2 pr-3 pl-10 text-sm leading-6 placeholder-gray-400 focus:border-primary-500 focus:ring-3 focus:ring-primary-500/50 dark:border-gray-700 dark:bg-gray-800 dark:focus:border-primary-500')
            elif isinstance(widget, (forms.Select, forms.ChoiceField)):
                add_form_field_class(widget, 'block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm font-semibold leading-5 focus:border-blue-500 focus:ring focus:ring-blue-500/50 dark:border-gray-700 dark:bg-gray-800 dark:focus:border-blue-500 sm:w-36')

class BaseForm(StyledFormMixin, forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()

class BaseModelForm(StyledFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()

class LoginForm(BaseForm):
    username = forms.CharField(
        label='Username',
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Username...',
            'required': True,
            'name': 'username',
        }),
        required=True
    )
    password = forms.CharField(
        label='Password',
        max_length=100,
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password...',
            'required': True,
            'name': 'password',
        }),
        required=True
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            raise ValidationError("Username does not exist.")
        return username
    
    class Meta:
        model = User
        fields = ['username', 'password']


class ContactForm(BaseForm):
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'First Name', 'required': True}),
        required=True
    )
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'required': True}),
        required=True
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Email', 'required': True}),
        required=True
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Your Message...', 'rows': 6, 'required': True}),
        required=True
    )

    def send_email(self, email_service: EmailService):
        email_service.send_email(
            to=self.cleaned_data["email"],
            subject= f"{COMPANY_NAME}: +  Contact Form Submission",
            body=self.cleaned_data["message"]
        )

class QuoteForm(BaseModelForm):
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
    message = forms.CharField(
        label="(OPTIONAL) Give us a few details about your event",
        widget=forms.Textarea(attrs={
            'placeholder': "It's a networking event with 50 people for 4 hours...",
            'rows': 3
        }),
        required=False
    )
    opt_in_text_messaging = forms.BooleanField(
        required=False,
        initial=True,
        widget=ToggleSwitchWidget(attrs={
            'id': 'opt_in_text_messaging',
            'message': 'I consent to receiving text message notifications.',
            'data-modal-id': 'quoteModal',
            'class': 'openModal',
        }),
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
        fields = ['full_name', 'phone_number', 'message', 'opt_in_text_messaging']

class ServiceForm(BaseModelForm):
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.all(),
        label="Service Type*",
        widget=forms.Select(attrs={
            'name': 'service_type',
            'required': True
        }),
        required=True
    )

    service = forms.CharField(
        max_length=255,
        label="Service Name*",
        widget=forms.TextInput(attrs={
            'name': 'service',
            'required': True
        }),
        required=True
    )

    suggested_price = forms.FloatField(
        label="Suggested Price",
        widget=forms.NumberInput(attrs={
            'name': 'suggested_price',
            'step': '0.01'
        }),
        required=False
    )

    guest_ratio = forms.IntegerField(
        label="Guest Ratio",
        widget=forms.NumberInput(attrs={
            'name': 'guest_ratio',
            'min': 1
        }),
        required=False
    )

    unit_type = forms.ModelChoiceField(
        queryset=UnitType.objects.all(),
        label="Unit Type*",
        widget=forms.Select(attrs={
            'name': 'unit_type',
            'required': True
        }),
        required=True
    )

    class Meta:
        model = Service
        fields = ['service_type', 'service', 'suggested_price', 'guest_ratio', 'unit_type']

class UserForm(BaseModelForm):
    username = forms.CharField(
        label="Username*",
        widget=forms.TextInput(attrs={'name': 'username', 'required': True}),
        required=True
    )

    first_name = forms.CharField(
        label="First Name*",
        widget=forms.TextInput(attrs={'name': 'first_name', 'required': True}),
        required=True
    )

    last_name = forms.CharField(
        label="Last Name*",
        widget=forms.TextInput(attrs={'name': 'last_name', 'required': True}),
        required=True
    )

    phone_number = forms.CharField(
        label="Phone Number*",
        widget=forms.TextInput(attrs={'name': 'phone_number', 'required': True}),
        required=True
    )

    forward_phone_number = forms.CharField(
        label="Forwarding Number*",
        widget=forms.TextInput(attrs={'name': 'forward_phone_number', 'required': True}),
        required=True
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name',
            'phone_number', 'forward_phone_number'
        ]

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    def save(self, commit=True):
        user = super().save()
        return user