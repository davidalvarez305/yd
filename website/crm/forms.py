from datetime import datetime
from django import forms

from core.models import Ad, CallTrackingNumber, CocktailIngredient, EventCocktail, EventShoppingList, EventStaff, EventStatus, FacebookAccessToken, HTTPLog, Ingredient, InternalLog, Invoice, InvoiceType, LandingPage, LandingPageTrackingNumber, Lead, LeadMarketingMetadata, LeadStatus, LeadStatusEnum, LeadStatusHistory, Message, Quote, QuotePreset, QuotePresetService, QuoteService, Service, StoreItem, Visit
from core.forms import BaseModelForm, DataAttributeModelSelect, StyledFilterForm
from core.models import LeadMarketing, Cocktail, Event
from crm.utils import calculate_quote_service_values, create_extension_invoice, update_quote_invoices
from core.widgets import BoxedCheckboxSelectMultiple, ContainedCheckboxSelectMultiple
from core.utils import normalize_phone_number
from core.logger import logger

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
        widget=forms.Select(attrs={'placeholder': 'Select a status', 'disabled': True}),
    )

    def clean_phone_number(self):
        return normalize_phone_number(self.cleaned_data.get('phone_number'))
    
    class Meta:
        model = Lead
        fields = ['full_name', 'phone_number', 'message', 'lead_status']

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

    def save(self, commit=True):
        event = super().save(commit)
        event.lead.change_lead_status(LeadStatusEnum.EVENT_BOOKED, event=event)
        return event

    class Meta:
        model = Event
        fields = [
            'start_time', 'end_time', 'date_paid', 'lead',
            'street_address', 'street_address_two', 'city', 'zip_code',
            'amount', 'tip', 'guests', 'special_instructions'
        ]

class LeadMarketingForm(BaseModelForm):
    ip = forms.GenericIPAddressField(
        label="IP Address",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., 192.168.1.1'
        })
    )

    user_agent = forms.CharField(
        label="User Agent",
        required=False,
        widget=forms.TextInput()
    )

    instant_form_lead_id = forms.GenericIPAddressField(
        label="FB Lead ID",
        required=False,
        widget=forms.TextInput()
    )

    referred_by = forms.ModelChoiceField(
        queryset=Lead.objects.all(),
        required=False,
        label="Referred By",
        widget=forms.Select()
    )

    ad = forms.ModelChoiceField(
        queryset=Ad.objects.all(),
        required=False,
        label="Ad",
        widget=forms.Select()
    )

    class Meta:
        model = LeadMarketing
        fields = ['ip', 'ad', 'user_agent', 'instant_form_lead_id']
    
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

class VisitForm(BaseModelForm):
    class Meta:
        model = Visit
        fields = ['session_duration']

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
        self.fields['adults'].error_messages = {'required': ''}
        self.fields['minors'].error_messages = {'required': ''}
        self.fields['hours'].error_messages = {'required': ''}

    class Meta:
        model = Quote
        fields = ['lead', 'adults', 'minors', 'hours', 'event_date']
        widgets = {
            'lead': forms.HiddenInput(),
            'event_date': forms.DateInput(attrs={
                'type': 'date'
            }),
            'adults': forms.NumberInput(attrs={'id': 'adults'}),
            'minors': forms.NumberInput(attrs={'id': 'minors' }),
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
                adults=instance.adults,
                minors=instance.minors,
                hours=instance.hours,
                suggested_price=quote_service.service.suggested_price, # Use quote_service.service.price_per_unit in order to always use the 'default' price, not the current price
                unit_type=quote_service.service.unit_type.type,
                service_type=quote_service.service.service_type.type,
                guest_ratio=quote_service.service.guest_ratio,
                date=instance.event_date,
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
        queryset=Service.objects.all().order_by('service'),
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
    
    def clean(self):
        cleaned_data = super().clean()
        quote = self.cleaned_data.get('quote')
        if quote.is_paid_off() and not self.instance.is_extend_service():
            raise forms.ValidationError('Paid off quote cannot be modified.')
        return cleaned_data
    
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

class QuotePresetEditFormForm(BaseModelForm):
    class Meta:
        model = QuotePreset
        fields = ['name', 'text_content']

class QuotePresetServiceForm(BaseModelForm):
    class Meta:
        model = QuotePresetService
        fields = '__all__'
        widgets = {
            'quote_preset': forms.Select(),
            'service': forms.Select(),
        }

class QuickQuoteForm(BaseModelForm):
    presets = forms.ModelMultipleChoiceField(
        queryset=QuotePreset.objects.all(),
        label="Seleccionar Paquetes",
        widget=BoxedCheckboxSelectMultiple(),
    )

    def clean_presets(self):
        presets = self.cleaned_data.get('presets')
        if not presets or len(presets) == 0:
            raise forms.ValidationError("You must select at least one preset.")
        return presets
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['adults'].error_messages = {'required': ''}
        self.fields['minors'].error_messages = {'required': ''}
        self.fields['hours'].error_messages = {'required': ''}
        self.fields['event_date'].error_messages = {'required': ''}
        self.fields['presets'].error_messages = {'required': ''}

    class Meta:
        model = Quote
        fields = ['lead', 'adults', 'minors', 'hours', 'event_date']
        widgets = {
            'lead': forms.HiddenInput(),
            'event_date': forms.DateInput(attrs={
                'type': 'date'
            }),
            'adults': forms.NumberInput(attrs={'id': 'adults'}),
            'minors': forms.NumberInput(attrs={'id': 'minors'}),
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

class InvoiceForm(BaseModelForm):
    class Meta:
        model = Invoice
        fields = ['date_paid', 'amount']
        widgets = {
            'date_paid': forms.DateTimeInput(attrs={
                'required': True,
                'name': 'date_paid',
                'type': 'datetime-local',
            })
        }

class LeadMarketingMetadataForm(BaseModelForm):
    class Meta:
        model = LeadMarketingMetadata
        fields = ['key', 'value', 'lead_marketing']
        widgets = {
            'lead': forms.HiddenInput(),
        }

class LandingPageForm(BaseModelForm):
    call_tracking_number = forms.ModelChoiceField(
        queryset=CallTrackingNumber.objects.all(),
        required=True,
        label="Tracking Number",
    )

    class Meta:
        model = LandingPage
        fields = ["name", "template_name", "is_active", "is_control", "call_tracking_number"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            latest = self.instance.tracking_numbers.order_by('-date_assigned').first()
            if latest:
                self.fields["call_tracking_number"].initial = latest.call_tracking_number
        
    def save(self, commit=True):
        landing_page = super().save(commit)

        call_tracking_number = self.cleaned_data.get("call_tracking_number")

        LandingPageTrackingNumber.objects.create(
            landing_page=landing_page,
            call_tracking_number=call_tracking_number,
        )

        return landing_page

class EventClientConfirmationForm(forms.Form):
    event = forms.ModelChoiceField(
        queryset=Event.objects.all(),
        widget=forms.HiddenInput()
    )

class MarketingAnalyticsFilterForm(StyledFilterForm):
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="From"
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="To"
    )

    MIN_DATE = datetime(2025, 10, 1).date()

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from") or self.MIN_DATE
        date_to = cleaned_data.get("date_to") or datetime.today().date()

        if date_from < self.MIN_DATE:
            date_from = self.MIN_DATE

        if date_to < date_from:
            raise forms.ValidationError("End date must be after start date.")

        cleaned_data["date_from"] = date_from
        cleaned_data["date_to"] = date_to
        return cleaned_data

class EventFilterForm(StyledFilterForm):
    lead = forms.ModelChoiceField(
        queryset=Lead.objects.all(),
        required=False,
        label="Lead"
    )

    date_from = forms.DateTimeField(
        required=False,
        label="Date From",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    date_to = forms.DateTimeField(
        required=False,
        label="Date To",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )