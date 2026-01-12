from io import BytesIO
import mimetypes
import os

from core.messaging.utils import MIME_EXTENSION_MAP
from website.settings import COMPANY_NAME
from .utils import add_form_field_class, cleanup_dir_files, convert_audio_format, convert_video_to_mp4, create_generic_file_name, get_upload_sub_dir, normalize_phone_number
from .widgets import ToggleSwitchWidget
from .models import Lead, Service, UnitType, User, ServiceType
from core.email import email_service

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from django import forms
from django.core.exceptions import ValidationError

class MultiFileInput(forms.FileInput):
    allow_multiple_selected = True

class MultiFileField(forms.FileField):
    widget = MultiFileInput

    def clean(self, data, initial=None):
        files = data or []
        if self.required and not files:
            raise forms.ValidationError(self.error_messages['required'], code='required')
        return files
    
class DataAttributeModelSelect(forms.Select):
    def __init__(self, attrs=None, opt_attrs=None):
        super().__init__(attrs)
        self.opt_attrs = opt_attrs or (lambda instance: {})

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if hasattr(value, 'instance'):
            extra_attrs = self.opt_attrs(value.instance)
            option['attrs'].update(extra_attrs)
        return option

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
                add_form_field_class(widget, 'size-4 rounded border border-gray-200 text-primary-500 checked:border-primary-500 focus:border-primary-500 focus:ring focus:ring-primary-500/50 dark:border-gray-600 dark:bg-gray-800 dark:ring-offset-gray-900 dark:checked:border-transparent dark:checked:bg-primary-500 dark:focus:border-primary-500')
            
            add_form_field_class(widget, 'font-medium')

class FilterFormMixin:
    def apply_styling(self):
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.TextInput, forms.EmailInput, forms.PasswordInput, forms.Textarea)):
                add_form_field_class(widget, 'block w-full rounded-lg border border-gray-200 py-2 pr-3 pl-10 text-sm leading-6 placeholder-gray-400 focus:border-primary-500 focus:ring-3 focus:ring-primary-500/50 dark:border-gray-700 dark:bg-gray-800 dark:focus:border-primary-500')
            elif isinstance(widget, (forms.Select, forms.ChoiceField)):
                add_form_field_class(widget, 'block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm font-semibold leading-5 focus:border-blue-500 focus:ring focus:ring-blue-500/50 dark:border-gray-700 dark:bg-gray-800 dark:focus:border-blue-500 sm:w-36')

class NormalizeEmptyStringsMixin:
    def normalize_empty_string(self, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def clean(self):
        cleaned_data = super().clean()
        for field_name, value in cleaned_data.items():
            field = self.fields.get(field_name)
            if isinstance(field, (forms.CharField, forms.TextInput, forms.Textarea)):
                cleaned_data[field_name] = self.normalize_empty_string(value)
        return cleaned_data

class BaseForm(StyledFormMixin, forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()

class StyledFilterForm(FilterFormMixin, forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()

class BaseModelForm(StyledFormMixin, NormalizeEmptyStringsMixin, forms.ModelForm):
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

    def send_email(self):
        email_service.send_email(
            to=self.cleaned_data.get('email'),
            subject= f"{COMPANY_NAME}: +  Contact Form Submission",
            body=self.cleaned_data.get('message')
        )

from django import forms
from django.utils import timezone
from datetime import timedelta

class LeadForm(BaseModelForm):
    full_name = forms.CharField(
        max_length=100,
        label="Full Name*",
        widget=forms.TextInput(attrs={
            'autocomplete': 'name',
            'required': True
        }),
        required=True
    )

    phone_number = forms.CharField(
        max_length=15,
        label="Phone Number*",
        widget=forms.TextInput(attrs={
            'autocomplete': 'tel-national',
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
            'data-modal-id': 'optinConfirmationModal',
            'class': 'openModal',
        }),
        label='',
    )

    # Bot-prevention fields (hidden)
    hp_field = forms.CharField(required=False, widget=forms.HiddenInput)
    modal_opened = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)
    opened_at = forms.DateTimeField(required=False, widget=forms.HiddenInput)
    js_enabled = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)

    def clean_hp_field(self):
        if self.cleaned_data.get("hp_field"):
            raise forms.ValidationError("Invalid submission.")
        return ""

    def clean(self):
        cleaned = super().clean()

        # Modal must be opened
        if not cleaned.get("modal_opened"):
            raise forms.ValidationError("Invalid submission flow.")

        # JS must be enabled
        if not cleaned.get("js_enabled"):
            raise forms.ValidationError("JavaScript required.")

        # Timing check (e.g. must take ≥ 1 seconds)
        opened_at = cleaned.get("opened_at")
        if opened_at:
            if timezone.now() - opened_at < timedelta(seconds=1):
                raise forms.ValidationError("Submission too fast.")
        else:
            raise forms.ValidationError("Invalid timing data.")

        return cleaned

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')

        if not phone_number:
            raise forms.ValidationError('Phone number field cannot be empty.')

        cleaned_phone_number = normalize_phone_number(phone_number)

        if not cleaned_phone_number:
            raise forms.ValidationError('Phone number field cannot be empty.')

        if Lead.objects.filter(phone_number=cleaned_phone_number).exists():
            raise forms.ValidationError(
                'Someone has already submitted a request from this phone number.'
            )

        return cleaned_phone_number

    class Meta:
        model = Lead
        fields = [
            'full_name',
            'phone_number',
            'message',
            'opt_in_text_messaging',
            'hp_field',
            'modal_opened',
            'opened_at',
            'js_enabled',
        ]

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

class AttachmentProcessingError(Exception):
    pass

class MultiMediaFileField(forms.FileField):
    widget = MultiFileInput

    def __init__(self, *args, **kwargs):
        field_name = kwargs.pop('field_name', None)
        if not field_name:
            raise AttributeError("MultiMediaFileField requires a 'field_name' argument.")

        self.field_name = field_name
        self.upload_root = getattr(settings, "UPLOADS_ROOT", os.path.join(settings.BASE_DIR, "uploads"))
        os.makedirs(self.upload_root, exist_ok=True)
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        files = data or []
        if self.required and not files:
            raise forms.ValidationError(self.error_messages['required'], code='required')

        media_files = []

        for file in files:
            content_type = getattr(file, 'content_type', '')
            source_ext = mimetypes.guess_extension(content_type) or MIME_EXTENSION_MAP.get(content_type, '.bin')
            sub_dir = get_upload_sub_dir(content_type)
            target_dir = os.path.join(self.upload_root, sub_dir)
            os.makedirs(target_dir, exist_ok=True)

            try:
                if content_type.startswith('audio/'):
                    target_file_name = create_generic_file_name(content_type, '.mp3')
                    target_file_path = os.path.join(target_dir, target_file_name)

                    target_file = convert_audio_format(file=file, target_file_path=target_file_path, to_format='mp3')
                    target_content_type = 'audio/mpeg'

                    target_file.seek(0)
                    file_size = len(target_file.read())
                    target_file.seek(0)

                    uploaded_file = self._build_uploaded_file(
                        file_obj=target_file,
                        name=target_file_name,
                        content_type=target_content_type,
                        size=file_size,
                        charset=getattr(file, 'charset', None),
                    )
                elif content_type.startswith('video/'):
                    target_file_name = create_generic_file_name(content_type, '.mp4')
                    target_file_path = os.path.join(target_dir, target_file_name)
                    target_content_type = 'video/mp4'

                    source_file_path = os.path.join(target_dir, create_generic_file_name(content_type, source_ext))
                    with open(source_file_path, 'wb') as f:
                        for chunk in file.chunks():
                            f.write(chunk)

                    convert_video_to_mp4(source_file_path, target_file_path)

                    with open(target_file_path, 'rb') as f:
                        target_video_file = f.read()

                    uploaded_file = self._build_uploaded_file(
                        file_obj=BytesIO(target_video_file),
                        name=target_file_name,
                        content_type=target_content_type,
                        size=len(target_video_file),
                        charset=getattr(file, 'charset', None),
                    )
                else:
                    uploaded_file = self._build_uploaded_file(
                        file_obj=file.file,
                        name=create_generic_file_name(content_type, source_ext),
                        content_type=content_type,
                        size=file.size,
                        charset=getattr(file, "charset", None),
                    )

                media_files.append(uploaded_file)

            except Exception as e:
                raise forms.ValidationError(f"File processing failed: {str(e)}")
            
            finally:
                cleanup_dir_files(self.upload_root)

        return media_files

    def _build_uploaded_file(self, file_obj, name, content_type, size, charset=None):
        return InMemoryUploadedFile(
            file=file_obj,
            field_name=self.field_name,
            name=name,
            content_type=content_type,
            size=size,
            charset=charset
        )