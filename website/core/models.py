from enum import Enum
import json
import os
from typing import Union
from django.db import models
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.db.models import Q, Sum
from django.utils.timezone import now

from marketing.enums import ConversionServiceType
from .signals import lead_status_changed

class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required")
        user = self.model(username=username, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True)
    phone_number = models.CharField(max_length=20, unique=True)
    forward_phone_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    events = models.ManyToManyField('Event', related_name='staff', through='EventStaff')

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number', 'forward_phone_number']

    objects = UserManager()

    class Meta:
        db_table = 'user'

    def __str__(self):
        return self.first_name + " " + self.last_name


class LeadStatusEnum(Enum):
    LEAD_CREATED = 'Lead Created'
    INVOICE_SENT = 'Invoice Sent'
    EVENT_BOOKED = 'Event Booked'

    def __str__(self):
        return self.name

class LeadStatus(models.Model):
    lead_status_id = models.AutoField(primary_key=True)
    status = models.CharField(
        max_length=50,
        choices=[(status.name, status.value) for status in LeadStatusEnum]
    )

    def __str__(self):
        return self.status
    
    class Meta:
        db_table = 'lead_status'

class LeadStatusHistory(models.Model):
    lead_status_history_id = models.AutoField(primary_key=True)
    lead = models.ForeignKey('Lead', on_delete=models.CASCADE)
    lead_status = models.ForeignKey('LeadStatus', on_delete=models.CASCADE)
    date_changed = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lead {self.lead.id} - Status {self.lead_status.get_status_display()} on {self.date_changed}"

    class Meta:
        db_table = 'lead_status_history'

class LeadInterest(models.Model):
    lead_interest_id = models.AutoField(primary_key=True)
    interest = models.CharField(max_length=100)

    def __str__(self):
        return self.interest
    
    class Meta:
        db_table = 'lead_interest'

class NextAction(models.Model):
    next_action_id = models.AutoField(primary_key=True)
    action = models.CharField(max_length=255)

    def __str__(self):
        return self.action
    
    class Meta:
        db_table = 'next_action'

class Lead(models.Model):
    lead_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, unique=True)
    opt_in_text_messaging = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    email = models.EmailField(null=True, unique=True)
    message = models.TextField(null=True)
    lead_status = models.ForeignKey(LeadStatus, null=True, db_column='lead_status_id', on_delete=models.SET_NULL)
    lead_interest = models.ForeignKey(LeadInterest, db_column='lead_interest_id', null=True, on_delete=models.SET_NULL)
    actions = models.ManyToManyField('NextAction', through='LeadNextAction')
    stripe_customer_id = models.CharField(max_length=255, unique=True, null=True)

    search_vector = SearchVectorField(null=True)

    def __str__(self):
        return self.full_name
    
    def phone_calls(self):
        return PhoneCall.objects.filter(Q(call_from=self.phone_number) | Q(call_to=self.phone_number))
    
    def is_qualified(self):
        total_duration = self.phone_calls().aggregate(total=Sum('duration'))
        return total_duration.get('total', 0) > 120
    
    def messages(self):
        return Message.objects.filter(Q(text_from=self.phone_number) | Q(text_to=self.phone_number)).order_by('date_created')
    
    def unread_messages_count(self):
        return Message.objects.filter(text_to=self.phone_number, is_read=True).count()
    
    def visits(self):
        return Visit.objects.filter(lead_marketing=self.lead_marketing)
    
    def last_contact(self):
        last_msg = Message.objects.filter(
            Q(text_from=self.phone_number) | Q(text_to=self.phone_number)
        ).order_by('-date_created').first()

        last_call = PhoneCall.objects.filter(
            Q(call_from=self.phone_number) | Q(call_to=self.phone_number)
        ).order_by('-date_created').first()

        if last_msg and last_call:
            return last_msg if last_msg.date_created > last_call.date_created else last_call
        return last_msg or last_call
    
    def update_search_vector(self):
        return SearchVector('full_name') + SearchVector('phone_number')

    def change_lead_status(self, status: Union[str, LeadStatusEnum]):
        if isinstance(status, LeadStatusEnum):
            status = status.name

        lead_status = LeadStatus.objects.filter(status=status).first()

        if not lead_status:
            raise ValueError('Invalid lead status.')
        
        self.lead_status = lead_status
        self.save()

        LeadStatusHistory.objects.create(
            lead=self,
            lead_status=lead_status
        )

        lead_status_changed.send(sender=self.__class__, instance=self)

    def value(self) -> float:
        result = self.events.aggregate(total=Sum('amount'))
        return result.get('total') or 0.0

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.__class__.objects.filter(pk=self.pk).update(
            search_vector=SearchVector('full_name', 'phone_number')
        )
    
    class Meta:
        db_table = 'lead'

class LeadNextAction(models.Model):
    lead_next_action_id = models.AutoField(primary_key=True)
    next_action = models.ForeignKey(NextAction, db_column='next_action_id', on_delete=models.CASCADE)
    lead = models.ForeignKey(Lead, db_column='lead_id', on_delete=models.CASCADE)
    action_date = models.DateTimeField()

    class Meta:
        db_table = 'lead_next_action'

class ServiceType(models.Model):
    service_type_id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=100)

    def __str__(self):
        return self.type

    class Meta:
        db_table = 'service_type'

class UnitType(models.Model):
    unit_type_id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=100)

    def __str__(self):
        return self.type

    class Meta:
        db_table = 'unit_type'

class Quote(models.Model):
    quote_id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=100)
    lead = models.ForeignKey(Lead, related_name='quotes', db_column='lead_id', on_delete=models.CASCADE)
    guests = models.IntegerField()
    hours = models.FloatField()
    event_date = models.DateTimeField()

    services = models.ManyToManyField('core.Service', related_name='quote_services', through='QuoteService')

    class Meta:
        db_table = 'quote'

    def amount(self) -> float:
        return sum(float(qs.units) * float(qs.price_per_unit) for qs in self.quote_services.all())

class Service(models.Model):
    service_id = models.AutoField(primary_key=True)
    service_type = models.ForeignKey(ServiceType, db_column='service_type_id', on_delete=models.RESTRICT)
    service = models.CharField(max_length=255)
    suggested_price = models.FloatField(null=True)
    guest_ratio = models.IntegerField(null=True)
    unit_type = models.ForeignKey(UnitType, db_column='unit_type_id', on_delete=models.RESTRICT)

    def __str__(self):
        return self.service

    class Meta:
        db_table = 'service'

class QuoteService(models.Model):
    quote_service_id = models.AutoField(primary_key=True)
    service = models.ForeignKey(Service, db_column='service_id', on_delete=models.RESTRICT)
    quote = models.ForeignKey(Quote, related_name='quote_services', db_column='quote_id', on_delete=models.RESTRICT)
    units = models.FloatField()
    price_per_unit = models.FloatField()

    def __str__(self):
        return self.service

    class Meta:
        db_table = 'quote_service'

class InvoiceType(models.Model):
    invoice_type_id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=100)
    amount_percentage = models.FloatField()

    def __str__(self):
        return self.type

    class Meta:
        db_table = 'invoice_type'

class Invoice(models.Model):
    invoice_id = models.AutoField(primary_key=True)
    quote = models.ForeignKey(Quote, related_name='invoices', db_column='quote_id', on_delete=models.CASCADE)
    date_created = models.DateTimeField()
    date_paid = models.DateTimeField()
    due_date = models.DateTimeField()
    invoice_type = models.ForeignKey(InvoiceType, db_column='invoice_type_id', on_delete=models.RESTRICT)
    url = models.TextField(max_length=255)
    stripe_invoice_id = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'invoice'

class LeadNote(models.Model):
    lead_note_id = models.AutoField(primary_key=True)
    note = models.TextField()
    lead = models.ForeignKey(Lead, related_name='notes', db_column='lead_id', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='notes', db_column='added_by_user_id', on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.note

    class Meta:
        db_table = 'lead_note'

class Message(models.Model):
    message_id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=255, unique=True)
    text = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    text_from = models.CharField(max_length=10)
    text_to = models.CharField(max_length=10)
    is_inbound = models.BooleanField(default=False)
    status = models.CharField(max_length=50)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = "message"
        indexes = [
            models.Index(fields=["text_from"]),
            models.Index(fields=["text_to"]),
            models.Index(fields=["is_read"]),
        ]

    def save(self, *args, **kwargs):
        self.text_from = self.text_from[-10:]
        self.text_to = self.text_to[-10:]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.external_id

    def get_lead(self):
        return Lead.objects.filter(phone_number=self.text_from).first() or Lead.objects.filter(phone_number=self.text_to).first()

    def images(self):
        return self.media.filter(content_type__startswith="image/")

    def videos(self):
        return self.media.filter(content_type__startswith="video/")

    def audios(self):
        return self.media.filter(content_type__startswith="audio/")

def media_upload_path(instance, filename):
    if instance.content_type.startswith("image/"):
        subdir = "images"
    elif instance.content_type.startswith("audio/"):
        subdir = "audio"
    elif instance.content_type.startswith("video/"):
        subdir = "videos"
    else:
        subdir = "other"

    return os.path.join("uploads", subdir, filename)

class MessageMedia(models.Model):
    message_media_id = models.AutoField(primary_key=True)
    message = models.ForeignKey(Message, related_name="media", on_delete=models.CASCADE)
    content_type = models.CharField(max_length=100)
    file = models.FileField(upload_to=media_upload_path)

    class Meta:
        db_table = "message_media"

    def __str__(self):
        return f"{self.content_type} - {self.file.name}"

    def is_image(self):
        return self.content_type.startswith("image/")

    def is_audio(self):
        return self.content_type.startswith("audio/")

    def is_video(self):
        return self.content_type.startswith("video/")

    @property
    def media_type(self):
        if self.content_type.startswith("image/"):
            return "image"
        elif self.content_type.startswith("video/"):
            return "video"
        elif self.content_type.startswith("audio/"):
            return "audio"
        return "other"

class PhoneCall(models.Model):
    phone_call_id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=255, unique=True)
    call_duration = models.IntegerField()
    date_created = models.DateTimeField()
    call_from = models.CharField(max_length=10)
    call_to = models.CharField(max_length=10)
    is_inbound = models.BooleanField(default=False)
    recording_url = models.TextField(null=True)
    status = models.CharField(max_length=50)

    class Meta:
        db_table = "phone_call"

    def save(self, *args, **kwargs):
        self.call_from = self.call_from[-10:]
        self.call_to = self.call_to[-10:]
        super().save(*args, **kwargs)
    
    def get_lead(self):
        from core.models import Lead
        return Lead.objects.filter(phone_number=self.call_from).first() or Lead.objects.filter(phone_number=self.call_to).first()

    def __str__(self):
        return self.external_id

class PhoneCallTranscription(models.Model):
    phone_call_transcription_id = models.AutoField(primary_key=True)
    phone_call = models.ForeignKey(PhoneCall, related_name='transcriptions', on_delete=models.CASCADE, db_column='phone_call_id')
    external_id = models.CharField(max_length=255, unique=True)
    text = models.TextField()
    audio = models.FileField(upload_to='audio/')
    job = models.JSONField(null=True)

    class Meta:
        db_table = "phone_call_transcription"

    def __str__(self):
        return self.external_id

AD_PLATFORMS = [
    (ConversionServiceType.GOOGLE.value, "Google"),
    (ConversionServiceType.FACEBOOK.value, "Facebook"),
]

class InstantForm(models.Model):
    instant_form_id = models.BigIntegerField()
    name = models.CharField(max_length=255, null=True)

class MarketingCampaign(models.Model):
    marketing_campaign_id = models.BigIntegerField()
    name = models.TextField()
    platform_id = models.IntegerField(choices=AD_PLATFORMS)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'marketing_campaign'
        unique_together = ('marketing_campaign_id', 'platform_id')

class LeadMarketing(models.Model):
    lead_marketing_id = models.AutoField(primary_key=True)
    lead = models.OneToOneField(Lead, related_name='lead_marketing', db_column='lead_id', on_delete=models.CASCADE)
    source = models.CharField(max_length=255, null=True)
    medium = models.CharField(max_length=255, null=True)
    channel = models.CharField(max_length=255, null=True)
    landing_page = models.TextField(null=True)
    keyword = models.CharField(max_length=255, null=True)
    referrer = models.TextField(null=True)
    click_id = models.TextField(unique=True, null=True)
    client_id = models.TextField(unique=True, null=True)
    button_clicked = models.CharField(max_length=255, null=True)
    ip = models.GenericIPAddressField(null=True)
    external_id = models.CharField(max_length=255, db_index=True)
    instant_form_lead_id = models.BigIntegerField(null=True)
    instant_form = models.ForeignKey(InstantForm, null=True, related_name='lead_marketing', db_column='instant_form_id', on_delete=models.SET_NULL)
    marketing_campaign = models.ForeignKey(MarketingCampaign, null=True, related_name='lead_marketing', db_column='marketing_campaign_id', on_delete=models.SET_NULL)

    def __str__(self):
        return f"Marketing info for Lead {self.lead_id}"
    
    def is_instant_form_lead(self):
        return bool(self.instant_form_lead_id)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Visit.objects.filter(external_id=self.external_id).update(lead_marketing=self)

    class Meta:
        db_table = 'lead_marketing'

class HTTPLog(models.Model):
    http_log_id = models.AutoField(primary_key=True)
    date_created = models.DateTimeField(default=now)
    method = models.CharField(max_length=10)
    url = models.URLField()
    query_params = models.JSONField(null=True)
    payload = models.JSONField(null=True)
    headers = models.JSONField(null=True)
    response = models.JSONField(null=True)
    status_code = models.IntegerField(null=True)
    error = models.JSONField(null=True)
    duration_seconds = models.FloatField(null=True)
    retries = models.IntegerField(default=0)
    service_name = models.CharField(max_length=100)

    def __str__(self):
        return f"[{self.service_name}] {self.method} {self.url} ({self.status_code})"

    class Meta:
        db_table = 'http_log'
        ordering = ["-date_created"]

class CallTrackingNumber(models.Model):
    call_tracking_number_id = models.AutoField(primary_key=True)
    call_tracking_number = models.CharField(max_length=15)

    def __str__(self):
        return self.call_tracking_number

    class Meta:
        db_table = 'call_tracking_number'

class CallTracking(models.Model):
    call_tracking_id = models.AutoField(primary_key=True)
    call_tracking_number = models.ForeignKey(
        CallTrackingNumber,
        on_delete=models.CASCADE,
        db_column='call_tracking_number_id',
        related_name='calls'
    )
    date_assigned = models.DateTimeField()
    date_expires = models.DateTimeField()
    metadata = models.JSONField(null=True)
    external_id = models.CharField(max_length=255)

    def __str__(self):
        return str(self.call_tracking_number)

    class Meta:
        db_table = 'call_tracking'

class Cocktail(models.Model):
    cocktail_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'cocktail'
    
    def __str__(self):
        return self.name

class Event(models.Model):
    event_id = models.AutoField(primary_key=True)
    lead = models.ForeignKey(Lead, related_name='events', db_column='lead_id', on_delete=models.CASCADE)
    street_address = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=100, null=True)
    zip_code = models.CharField(max_length=20, null=True)
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_paid = models.DateTimeField(default=timezone.now)
    amount = models.FloatField()
    tip = models.FloatField(null=True)
    guests = models.IntegerField()
    cocktail = models.ManyToManyField(
        Cocktail,
        through='EventCocktail',
        related_name='events'
    )

    def __str__(self):
        return f"{self.lead}: {self.start_time.strftime('%B %d, %Y')} - {self.start_time.strftime('%#I %p')}"
    
    class Meta:
        db_table = 'event'

class EventCocktail(models.Model):
    event_cocktail_id = models.AutoField(primary_key=True)
    cocktail = models.ForeignKey(Cocktail, db_column='cocktail_id', on_delete=models.CASCADE)
    event = models.ForeignKey(Event, db_column='event_id', on_delete=models.CASCADE)

    class Meta:
        db_table = 'event_cocktail'
        unique_together = ('cocktail', 'event')

class EventRole(models.Model):
    event_role_id = models.AutoField(primary_key=True)
    role = models.CharField(max_length=100)

    def __str__(self):
        return self.role

    class Meta:
        db_table = 'event_role'

class EventStaff(models.Model):
    event_staff_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User,db_column='user_id', on_delete=models.RESTRICT)
    event = models.ForeignKey(Event, db_column='event_id', on_delete=models.CASCADE)
    event_role = models.ForeignKey(EventRole, db_column='event_role_id', on_delete=models.RESTRICT)
    hourly_rate = models.FloatField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        db_table = 'event_staff'

class Visit(models.Model):
    visit_id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=255, db_index=True)
    referrer = models.URLField(null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    url = models.URLField()
    session_duration = models.FloatField(default=0.0)
    
    lead_marketing = models.ForeignKey(LeadMarketing,
        null=True, on_delete=models.SET_NULL,
        related_name='visits'
    )

    def __str__(self):
        return f"Visit {self.visit_id} - {self.url} from {self.referrer}"

    class Meta:
        db_table = 'visit'
        ordering = ['-date_created']

class IngredientCategory(models.Model):
    ingredient_category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'ingredient_category'

class Store(models.Model):
    store_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'store'

class Ingredient(models.Model):
    ingredient_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    ingredient_category = models.ForeignKey(
        IngredientCategory,
        db_column='ingredient_category_id',
        on_delete=models.RESTRICT
    )
    store = models.ForeignKey(
        Store,
        db_column='store_id',
        on_delete=models.RESTRICT
    )

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'ingredient'

class Unit(models.Model):
    unit_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    abbreviation = models.CharField(max_length=20)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'unit'

class UnitConversion(models.Model):
    unit_conversion_id = models.AutoField(primary_key=True)
    from_ = models.ForeignKey(
        Unit,
        db_column='from',
        on_delete=models.CASCADE
    )
    to = models.ForeignKey(
        Unit,
        db_column='to',
        on_delete=models.CASCADE
    )
    multiplier = models.FloatField()

    def __str__(self):
        return f'{self.from_} to {self.to}'

    class Meta:
        db_table = 'unit'

class CocktailIngredient(models.Model):
    cocktail_ingredient_id = models.AutoField(primary_key=True)

    cocktail = models.ForeignKey(
        Cocktail,
        related_name='ingredients',
        db_column='cocktail_id',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredient,
        related_name='used_in_cocktails',
        db_column='ingredient_id',
        null=True,
        on_delete=models.SET_NULL
    )
    unit = models.ForeignKey(
        Unit,
        related_name='used_in_cocktails',
        db_column='unit_id',
        null=True,
        on_delete=models.SET_NULL
    )
    amount = models.FloatField()

    class Meta:
        db_table = 'cocktail_ingredient'
        unique_together = ('cocktail', 'ingredient', 'unit')