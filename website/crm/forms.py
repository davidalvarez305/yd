from http import HTTPStatus
from django import forms
import re

from django.urls import reverse

from core.models import Ad, CallTrackingNumber, CocktailIngredient, EventCocktail, EventShoppingList, EventStaff, FacebookAccessToken, HTTPLog, Ingredient, InternalLog, Invoice, InvoiceType, Lead, LeadStatus, LeadInterest, LeadStatusEnum, LeadStatusHistory, Message, Quote, QuotePreset, QuoteService, Service, StoreItem, Visit
from core.forms import BaseModelForm, BaseForm, DataAttributeModelSelect, FilterFormMixin
from core.models import LeadMarketing, Cocktail, Event
from marketing.enums import ConversionServiceType
from crm.utils import calculate_quote_service_values, create_extension_invoice, update_quote_invoices
from core.widgets import BoxedCheckboxSelectMultiple, ContainedCheckboxSelectMultiple
from core.messaging import messaging_service
from website import settings
from core.utils import format_text_message

class LeadForm(BaseModelForm):
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
            'rows': 3,
            'readonly': True
        }),
        required=False,
        disabled=True,
    )

    lead_status = forms.ModelChoiceField(
        queryset=LeadStatus.objects.all(),
        required=False,
        label="Lead Status",
        widget=forms.Select(attrs={'placeholder': 'Select a status'}),
    )

    lead_interest = forms.ModelChoiceField(
        queryset=LeadInterest.objects.all(),
        required=False,
        label="Lead Interest",
        widget=forms.Select(attrs={'placeholder': 'Select interest'})
    )

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if not re.match(r'^\+1\d{10}$|^\d{10}$|^\d{3}-\d{3}-\d{4}$|^\(\d{3}\) \d{3}-\d{4}$', phone_number):
            raise forms.ValidationError(
                'Enter a valid US phone number (e.g., +1XXXXXXXXXX, XXXXXXXXXX, XXX-XXX-XXXX, (XXX) XXX-XXXX)'
            )
        return phone_number
    
    def has_lead_status_changed(self):
        return 'lead_status' in self.changed_data

    def save(self):
        lead = Lead.objects.get(phone_number=self.cleaned_data.get('phone_number'))

        if self.has_lead_status_changed():
            status = self.cleaned_data.pop('lead_status')

            enum_status = LeadStatus.find_enum(status.pk)

            lead.change_lead_status(enum_status)
 
        lead.save()

        return lead

    class Meta:
        model = Lead
        fields = ['full_name', 'phone_number', 'message', 'lead_status', 'lead_interest']

class LeadFilterForm(FilterFormMixin, BaseForm):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search for a lead...',
            'id': 'search',
            'name': 'search',
        }),
    )

    lead_interest_id = forms.ModelChoiceField(
        queryset=LeadInterest.objects.all(),
        required=False,
        empty_label="Interest",
        widget=forms.Select(attrs={
            'id': 'lead_interest_id',
            'name': 'lead_interest_id',
        })
    )

    lead_status_id = forms.ModelChoiceField(
        queryset=LeadStatus.objects.all(),
        required=False,
        empty_label="Status",
        widget=forms.Select(attrs={
            'id': 'lead_status_id',
            'name': 'lead_status_id',
        })
    )

class CocktailForm(BaseModelForm):
    name = forms.CharField(
        max_length=255,
        label="Name*",
        widget=forms.TextInput(attrs={
            'required': True
        }),
        required=True
    )

    class Meta:
        model = Cocktail
        fields = ['name']

class EventForm(BaseModelForm):
    lead = forms.ModelChoiceField(
        queryset=Lead.objects.all(),
        required=True,
        empty_label="Lead",
        widget=forms.Select(attrs={
            'id': 'lead',
            'name': 'lead',
        })
    )

    start_time = forms.DateTimeField(
        label="Start Time*",
        widget=forms.DateTimeInput(attrs={
            'required': True,
            'name': 'start_time',
            'type': 'datetime-local',
        }),
        required=True
    )

    end_time = forms.DateTimeField(
        label="End Time*",
        widget=forms.DateTimeInput(attrs={
            'required': True,
            'name': 'end_time',
            'type': 'datetime-local',
        }),
        required=True
    )

    date_paid = forms.DateTimeField(
        label="Date Paid*",
        widget=forms.DateTimeInput(attrs={
            'required': True,
            'name': 'date_paid',
            'type': 'datetime-local',
        }),
        required=True
    )

    street_address = forms.CharField(
        max_length=255,
        label="Street Address",
        widget=forms.TextInput(attrs={'name': 'street_address'}),
        required=False
    )

    street_address_two = forms.CharField(
        max_length=255,
        label="Apt/Unit",
        widget=forms.TextInput(attrs={'name': 'street_address'}),
        required=False
    )

    city = forms.CharField(
        max_length=100,
        label="City",
        widget=forms.TextInput(attrs={'name': 'city'}),
        required=False
    )

    zip_code = forms.CharField(
        max_length=20,
        label="Zip Code",
        widget=forms.TextInput(attrs={'name': 'zip_code'}),
        required=False
    )

    amount = forms.FloatField(
        label="Amount*",
        widget=forms.NumberInput(attrs={
            'required': True,
            'name': 'amount',
        }),
        required=True
    )

    tip = forms.FloatField(
        label="Tip",
        widget=forms.NumberInput(attrs={'name': 'tip'}),
        required=False
    )

    guests = forms.IntegerField(
        label="Guests",
        widget=forms.NumberInput(attrs={'name': 'guests'}),
        required=True
    )

    special_instructions = forms.Textarea(
        attrs={
            'label': "Special Instructions",
            'required': False,
        },
    )

    class Meta:
        model = Event
        fields = [
            'start_time', 'end_time', 'date_paid', 'lead',
            'street_address', 'street_address_two', 'city', 'zip_code',
            'amount', 'tip', 'guests', 'special_instructions'
        ]

class LeadMarketingForm(BaseModelForm):
    source = forms.CharField(
        max_length=255,
        label="Source",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., Google, Facebook'
        })
    )

    medium = forms.CharField(
        max_length=255,
        label="Medium",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., CPC, email'
        })
    )

    channel = forms.CharField(
        max_length=255,
        label="Channel",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., Paid, Organic, Social'
        })
    )

    landing_page = forms.CharField(
        label="Landing Page URL",
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'https://example.com/landing-page',
            'rows': 2
        })
    )

    keyword = forms.CharField(
        max_length=255,
        label="Keyword",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., event catering nyc'
        })
    )

    click_id = forms.CharField(
        label="Click ID",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'gclid, fbclid, etc.'
        })
    )

    client_id = forms.CharField(
        label="Client ID",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Google Analytics Client ID'
        })
    )

    ip = forms.GenericIPAddressField(
        label="IP Address",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., 192.168.1.1'
        })
    )

    instant_form_lead_id = forms.IntegerField(
        label="Instant Form Lead ID",
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Meta lead form lead ID'
        })
    )

    referred_by = forms.ModelChoiceField(
        queryset=Lead.objects.all(),
        required=False,
        label="Referred By",
        widget=forms.Select(attrs={
            'placeholder': 'Select Lead'
        })
    )

    ad = forms.ModelChoiceField(
        queryset=Ad.objects.all(),
        required=False,
        label="Ad",
        widget=forms.Select(attrs={
            'placeholder': 'Select Ad'
        })
    )

    class Meta:
        model = LeadMarketing
        fields = [
            'source', 'medium', 'channel', 'landing_page', 'keyword',
            'click_id', 'client_id', 'ip', 'ad'
        ]
    
    def clean_referred_by(self):
        lead = self.cleaned_data.get('referred_by')
        if lead is None:
            return None

        try:
            return LeadMarketing.objects.get(lead=lead)
        except LeadMarketing.DoesNotExist:
            raise forms.ValidationError("The selected lead does not have marketing data.")

class CallTrackingNumberForm(BaseModelForm):
    class Meta:
        model = CallTrackingNumber
        fields = ['phone_number', 'forward_phone_number']

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

class LeadNoteForm(BaseModelForm):
    class Meta:
        fields = ['note']

class EventCocktailForm(BaseModelForm):
    class Meta:
        model = EventCocktail
        fields = ['cocktail', 'event']
        widgets = {
            'cocktail': forms.Select(),
            'event': forms.HiddenInput(),
        }

class EventStaffForm(BaseModelForm):
    start_time = forms.DateTimeField(
        label="Start Time*",
        widget=forms.DateTimeInput(attrs={
            'required': True,
            'name': 'start_time',
            'type': 'datetime-local',
        }),
        required=True
    )

    end_time = forms.DateTimeField(
        label="End Time*",
        widget=forms.DateTimeInput(attrs={
            'required': True,
            'name': 'end_time',
            'type': 'datetime-local',
        }),
        required=True
    )

    class Meta:
        model = EventStaff
        fields = ['user', 'event', 'event_role', 'hourly_rate', 'start_time', 'end_time']
        widgets = {
            'user': forms.Select(),
            'event_role': forms.Select(),
            'event': forms.HiddenInput(),
        }

class CocktailIngredientForm(BaseModelForm):
    amount = forms.FloatField(
        label="Amount*",
        widget=forms.NumberInput(attrs={
            'required': True,
            'name': 'amount',
        }),
        required=True
    )

    class Meta:
        model = CocktailIngredient
        fields = ['cocktail', 'ingredient', 'amount', 'unit']
        widgets = {
            'ingredient': forms.Select(),
            'unit': forms.Select(),
            'cocktail': forms.HiddenInput(),
        }

class IngredientForm(BaseModelForm):
    class Meta:
        model = Ingredient
        fields = '__all__'
        widgets = {
            'store': forms.Select(),
            'ingredient_category': forms.Select(),
        }
        
class EventShoppingListForm(BaseModelForm):
    class Meta:
        model = EventShoppingList
        fields = ['event']
        widgets = {
            'event': forms.HiddenInput(),
            'external_id': forms.HiddenInput(),
        }

class StoreItemForm(BaseModelForm):
    image = forms.ImageField(required=False)

    class Meta:
        model = StoreItem
        fields = '__all__'

class QuoteForm(BaseModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['event_date'].error_messages = {'required': ''}
        self.fields['guests'].error_messages = {'required': ''}
        self.fields['hours'].error_messages = {'required': ''}

    class Meta:
        model = Quote
        fields = ['lead', 'guests', 'hours', 'event_date']
        widgets = {
            'lead': forms.HiddenInput(),
            'event_date': forms.DateInput(attrs={
                'type': 'date'
            }),
            'guests': forms.NumberInput(attrs={'id': 'guests'}),
            'hours': forms.NumberInput(attrs={'id': 'hours'})
        }

    def clean(self):
        cleaned_data = super().clean()
        if self.instance.pk and self.instance.is_paid_off():
            raise forms.ValidationError('Quote cannot be modified.')
        return cleaned_data
    
    def save(self, commit=True):
        is_new = self.instance.pk is None
        instance = super().save(commit=commit)

        quote_services = instance.quote_services.all()
        for quote_service in quote_services:
            data = calculate_quote_service_values(
                guests=instance.guests,
                hours=instance.hours,
                suggested_price=quote_service.price_per_unit,
                unit_type=quote_service.service.unit_type.type,
                service_type=quote_service.service.service_type.type,
                guest_ratio=quote_service.service.guest_ratio,
            )
            quote_service.price_per_unit = data.get('price')
            quote_service.units = data.get('units')
            quote_service.save()
        
        if not is_new:
            update_quote_invoices(quote=instance)

        return instance

class QuoteSendForm(forms.Form):
    quote = forms.ModelChoiceField(
        queryset=Quote.objects.all(),
        widget=forms.HiddenInput()
    )

class QuoteServiceForm(BaseModelForm):
    service = forms.ModelChoiceField(
        queryset=Service.objects.all(),
        required=False,
        label="Service",
        widget=DataAttributeModelSelect(attrs={
            'placeholder': 'Select a status',
            'id': 'service'
        },
        opt_attrs=lambda instance: {
            'data-id': instance.pk,
            'data-service': instance.service_type,
            'data-unit': instance.unit_type,
            'data-price': instance.suggested_price,
            'data-ratio': instance.guest_ratio,
        }),
    )

    class Meta:
        model = QuoteService
        fields = ['service', 'quote', 'units', 'price_per_unit']
        widgets = {
            'quote': forms.HiddenInput(),
            'units': forms.NumberInput(attrs={'id': 'units'}),
            'price_per_unit': forms.NumberInput(attrs={'id': 'price'})
        }
    
    def save(self, commit=True):
        instance = super().save(commit)
        if instance.quote.is_paid_off():
            if instance.is_extend_service():
                create_extension_invoice(quote_service=instance)
        else:
            update_quote_invoices(quote=instance.quote)
        return instance

class QuotePresetForm(BaseModelForm):
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.all(),
        label="Seleccionar Paquetes",
        widget=ContainedCheckboxSelectMultiple(),
    )

    class Meta:
        model = QuotePreset
        fields = '__all__'

class QuickQuoteForm(BaseModelForm):
    presets = forms.ModelMultipleChoiceField(
        queryset=QuotePreset.objects.all(),
        label="Seleccionar Paquetes",
        widget=BoxedCheckboxSelectMultiple(),
    )

    def clean_presets(self):
        presets = self.cleaned_data.get('presets')
        empty_presets = "You must select at least one preset."
        if not presets:
            raise forms.ValidationError(empty_presets)
        if len(presets) == 0:
            raise forms.ValidationError(empty_presets)
        return presets
    
    def save(self):
        try:
            lead = self.cleaned_data.get('lead')
            guests = self.cleaned_data.get('guests')
            hours = self.cleaned_data.get('hours')
            event_date = self.cleaned_data.get('event_date')

            text_messages = []

            presets = self.cleaned_data.get('presets')
            for preset in presets:
                quote_services = []
                quote = Quote(
                    lead=lead,
                    guests=guests,
                    hours=hours,
                    event_date=event_date,
                )
                quote.save()
                services = preset.services.all()
                for service in services:
                    values = calculate_quote_service_values(
                        guests=guests,
                        hours=hours,
                        suggested_price=service.suggested_price,
                        service_type=service.service_type.type,
                        guest_ratio=service.guest_ratio,
                        unit_type=service.unit_type.type,
                    )
                    quote_service = QuoteService(
                        service = service,
                        quote = quote,
                        units = values.get('units'),
                        price_per_unit = values.get('price'),
                    )
                    quote_services.append(quote_service)
                QuoteService.objects.bulk_create(quote_services)
                text_messages.append({ 'message': preset.text_content, 'external_id': str(quote.external_id) })
                update_quote_invoices(quote=quote)

            text_content = ''
            for i, text in enumerate(text_messages):
                preset_content = text.get('message')
                external_id = text.get('external_id')
                path = reverse(viewname='external_quote_view', kwargs={'external_id': external_id})

                text_content += f"{preset_content}\n{settings.ROOT_DOMAIN}{path}"

                if i < len(text_messages) - 1:
                    text_content += "\n\n"

            message = Message(
                text=format_text_message(text_content),
                text_from=settings.COMPANY_PHONE_NUMBER,
                text_to=lead.phone_number,
                is_inbound=False,
                status='Sent',
                is_read=True,
            )
            resp = messaging_service.send_text_message(message=message)
            message.external_id = resp.sid
            message.status = resp.status
            message.save()

            lead.change_lead_status(LeadStatusEnum.INVOICE_SENT)
        except Exception as e:
            print(f'ERROR: {e}')
            raise Exception('Error saving quick quote form.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['guests'].error_messages = {'required': ''}
        self.fields['hours'].error_messages = {'required': ''}
        self.fields['event_date'].error_messages = {'required': ''}
        self.fields['presets'].error_messages = {'required': ''}

    class Meta:
        model = Quote
        fields = ['lead', 'guests', 'hours', 'event_date']
        widgets = {
            'lead': forms.HiddenInput(),
            'event_date': forms.DateInput(attrs={
                'type': 'date'
            }),
            'guests': forms.NumberInput(attrs={'id': 'guests'}),
            'hours': forms.NumberInput(attrs={'id': 'hours'})
        }

class InternalLogForm(BaseModelForm):
    class Meta:
        model = InternalLog
        fields = ['level', 'message', 'logger', 'pathname', 'lineno', 'exception']

class FacebookAccessTokenForm(BaseModelForm):
    class Meta:
        model = FacebookAccessToken
        fields = ['access_token']