from datetime import timedelta
from enum import Enum
from typing import Union
import uuid
from django.db import models
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

from marketing.enums import ConversionServiceType
from website import settings
from .utils import media_upload_path, save_image_path

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
    LEAD_CREATED = 'LEAD_CREATED'
    INVOICE_SENT = 'INVOICE_SENT'
    EVENT_BOOKED = 'EVENT_BOOKED'
    RE_ENGAGED = 'RE_ENGAGED'

    def __str__(self):
        return self.value
    
    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)

class LeadStatus(models.Model):
    lead_status_id = models.AutoField(primary_key=True)
    status = models.CharField(
        max_length=50,
        choices=[(status.name, status.value) for status in LeadStatusEnum]
    )

    def __str__(self):
        return self.status
    
    @classmethod
    def find_enum(cls, pk: int) -> LeadStatusEnum | None:
        try:
            lead_status = cls.objects.get(pk=pk)
            return LeadStatusEnum(lead_status.status)
        except (cls.DoesNotExist, ValueError):
            return None
    
    class Meta:
        db_table = 'lead_status'

class LeadStatusHistory(models.Model):
    lead_status_history_id = models.AutoField(primary_key=True)
    lead = models.ForeignKey('Lead', on_delete=models.CASCADE)
    lead_status = models.ForeignKey('LeadStatus', on_delete=models.RESTRICT)
    date_changed = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lead {self.lead.pk} - Status {self.lead_status.get_status_display()} on {self.date_changed}"

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
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=255, unique=True)
    opt_in_text_messaging = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    message = models.TextField(null=True)
    lead_status = models.ForeignKey(LeadStatus, null=True, db_column='lead_status_id', on_delete=models.SET_NULL)
    lead_interest = models.ForeignKey(LeadInterest, db_column='lead_interest_id', null=True, on_delete=models.SET_NULL)
    actions = models.ManyToManyField('NextAction', through='LeadNextAction')

    search_vector = SearchVectorField(null=True)

    def __str__(self):
        return self.full_name
    
    def phone_calls(self):
        return PhoneCall.objects.filter(Q(call_from=self.phone_number) | Q(call_to=self.phone_number))
    
    def is_inactive(self):
        two_weeks_ago = timezone.now() - timedelta(days=14)

        if self.created_at > two_weeks_ago:
            return False

        last_msg = self.messages().order_by('-date_created').first()
        last_call = self.phone_calls().order_by('-date_created').first()

        latest_activity = None
        if last_msg and last_call:
            latest_activity = max(last_msg.date_created, last_call.date_created)
        elif last_msg:
            latest_activity = last_msg.date_created
        elif last_call:
            latest_activity = last_call.date_created
        
        last_status = LeadStatusHistory.objects.filter(lead=self).order_by('-date_changed').first()

        return (not latest_activity and last_status.date_changed < two_weeks_ago) or latest_activity < two_weeks_ago
    
    def messages(self):
        return Message.objects.filter(Q(text_from=self.phone_number) | Q(text_to=self.phone_number)).order_by('date_created')
    
    def unread_messages_count(self):
        return Message.objects.filter(text_from=self.phone_number, is_read=False).count()
    
    def visits(self):
        return Visit.objects.filter(lead_marketing=self.lead_marketing)
    
    def last_contact(self):
        last_msg = Message.objects.filter(Q(text_from=self.phone_number) | Q(text_to=self.phone_number)).order_by('-date_created').first()
        last_call = PhoneCall.objects.filter(Q(call_from=self.phone_number) | Q(call_to=self.phone_number)).order_by('-date_created').first()

        if last_msg and last_call:
            return last_msg if last_msg.date_created > last_call.date_created else last_call
        return last_msg or last_call
    
    def update_search_vector(self):
        return SearchVector('full_name') + SearchVector('phone_number')

    def value(self, visited=None) -> float:
        if visited is None:
            visited = set()

        if self.pk in visited:
            return 0.0

        visited.add(self.pk)

        total = 0.0

        for quote in self.quotes.all():
            for invoice in quote.invoices.all():
                if invoice.date_paid:
                    total += invoice.amount

        for referral in self.lead_marketing.referrals.all():
            total += referral.lead.value(visited=visited)

        return total

    def change_lead_status(self, status: Union[str, LeadStatusEnum], event = None):
        from marketing.signals import lead_status_changed
        if isinstance(status, LeadStatusEnum):
            status = status.name

        lead_status = LeadStatus.objects.get(status=status)

        self.lead_status = lead_status
        self.save()

        log = LeadStatusHistory(
            lead=self,
            lead_status=lead_status
        )

        log.save()

        lead_status_changed.send(sender=self.__class__, instance=self, event=event)

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
    SERVICE = 'service'
    RENTAL = 'rental'
    FOOD = 'food'
    ADD_ON = 'add_on'
    ENTERTAINMENT = 'entertainment'
    EXTEND = 'extend'

    TYPE_CHOICES = [
        (SERVICE, 'Service'),
        (RENTAL, 'Rental'),
        (FOOD, 'Food'),
        (ADD_ON, 'Add On'),
        (ENTERTAINMENT, 'Entertainment'),
        (EXTEND, 'Extend')
    ]

    service_type_id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=100, choices=TYPE_CHOICES, unique=True)

    def __str__(self):
        return dict(self.TYPE_CHOICES).get(self.type, self.type)

    class Meta:
        db_table = 'service_type'

class UnitType(models.Model):
    PER_PERSON = 'per_person'
    HOURLY = 'hourly'
    FIXED = 'fixed'

    TYPE_CHOICES = [
        (PER_PERSON, 'Per Person'),
        (HOURLY, 'Hourly'),
        (FIXED, 'Fixed'),
    ]

    unit_type_id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=100, choices=TYPE_CHOICES, unique=True)

    def __str__(self):
        return dict(self.TYPE_CHOICES).get(self.type, self.type)

    class Meta:
        db_table = 'unit_type'

class Quote(models.Model):
    quote_id = models.AutoField(primary_key=True)
    external_id = models.UUIDField(unique=True, db_index=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, related_name='quotes', db_column='lead_id', on_delete=models.CASCADE)
    guests = models.IntegerField()
    hours = models.FloatField()
    event_date = models.DateField()

    services = models.ManyToManyField('core.Service', related_name='quote_services', through='QuoteService')

    def __str__(self):
        return str(self.external_id)

    class Meta:
        db_table = 'quote'

    def amount(self) -> float:
        return sum(float(qs.units) * float(qs.price_per_unit) for qs in self.quote_services.all())
    
    def total_due(self) -> float:
        invoices_due = self.amount()

        for invoice in self.invoices.all():
            if invoice.date_paid:
                invoices_due -= invoice.amount

        return invoices_due
    
    def is_within_week(self) -> bool:
        deposit_invoice = self.invoices.filter(invoice_type__type=InvoiceTypeEnum.DEPOSIT).first()

        if not deposit_invoice:
            raise Exception('No deposit invoice.')

        return timezone.now() >= deposit_invoice.due_date - timedelta(days=7)
    
    def is_deposit_paid(self) -> bool:
        deposit_invoice = self.invoices.filter(invoice_type__type=InvoiceType.objects.get(type=InvoiceTypeEnum.DEPOSIT.value)).first()

        if not deposit_invoice:
            raise Exception('No deposit invoice.')

        return deposit_invoice.date_paid is not None
    
    def get_deposit_paid_amount(self) -> bool:
        deposit_invoice = self.invoices.filter(invoice_type__type=InvoiceType.objects.get(type=InvoiceTypeEnum.DEPOSIT.value)).first()

        if not deposit_invoice:
            raise Exception('No deposit invoice.')
        
        if not deposit_invoice.date_paid:
            raise ValueError("Deposit isn't paid.")

        return deposit_invoice.amount
    
    def is_paid_off(self) -> bool:
        deposit_invoice = self.invoices.filter(invoice_type__type=InvoiceTypeEnum.DEPOSIT.value).first()
        remaining_invoice = self.invoices.filter(invoice_type__type=InvoiceTypeEnum.REMAINING.value).first()
        full_invoice = self.invoices.filter(invoice_type__type=InvoiceTypeEnum.FULL.value).first()

        return any([
            deposit_invoice and remaining_invoice and deposit_invoice.date_paid and remaining_invoice.date_paid,
            full_invoice and full_invoice.date_paid,
        ])
    
    def save(self, *args, **kwargs):
        from crm.utils import create_quote_due_date
        if self.pk:
            if self.is_paid_off():
                raise Exception('Quote cannot be modified if it is already paid off.')
            
            # Update invoice due dates if quote date changes
            for invoice in self.invoices.all():
                invoice.due_date = create_quote_due_date(event_date=self.event_date)
                invoice.save()
        
        return super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        if self.is_paid_off() or self.is_deposit_paid():
            raise Exception('Quote cannot be modified if it is already paid off.')
        return super().delete(*args, **kwargs)
    
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
    quote = models.ForeignKey(Quote, related_name='quote_services', db_column='quote_id', on_delete=models.CASCADE)
    units = models.FloatField()
    price_per_unit = models.FloatField()

    def __str__(self):
        return self.service.service
    
    @property
    def total(self):
        return self.units * self.price_per_unit
    
    def is_extend_service(self):
        return self.service.service_type.type == 'Extend'

    def can_modify_quote(self):
        return self.is_extend_service() or not self.quote.is_paid_off()

    def save(self, *args, **kwargs):
        if not self.can_modify_quote():
            raise Exception('Cannot modify quote which is paid off')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not self.can_modify_quote():
            raise Exception('Cannot modify quote which is paid off')
        return super().delete(*args, **kwargs)

    class Meta:
        db_table = 'quote_service'

class InvoiceTypeEnum(Enum):
    DEPOSIT = 'DEPOSIT'
    REMAINING = 'REMAINING'
    FULL = 'FULL'
    EXTEND = 'EXTEND'

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)

class InvoiceType(models.Model):
    invoice_type_id = models.AutoField(primary_key=True)
    type = models.CharField(
        max_length=50,
        choices=[(type.name, type.value) for type in InvoiceTypeEnum],
        db_index=True,
        unique=True
    )
    amount_percentage = models.FloatField()

    def __str__(self):
        return self.type

    class Meta:
        db_table = 'invoice_type'
    
def get_primary_invoices():
    return InvoiceType.objects.filter(pk__lt=5)

class Invoice(models.Model):
    invoice_id = models.AutoField(primary_key=True)
    quote = models.ForeignKey(Quote, related_name='invoices', db_column='quote_id', on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    date_paid = models.DateTimeField(null=True)
    amount = models.FloatField(null=True)
    due_date = models.DateTimeField()
    invoice_type = models.ForeignKey(InvoiceType, db_column='invoice_type_id', on_delete=models.RESTRICT)
    session_id = models.CharField(max_length=255, null=True)
    external_id = models.UUIDField(unique=True, db_index=True, default=uuid.uuid4, editable=False)
    receipt = models.FileField(upload_to='receipts/', null=True)

    class Meta:
        db_table = 'invoice'

    def save(self, *args, **kwargs):
        is_existing = self.pk is not None
        old_invoice = Invoice.objects.get(pk=self.pk) if is_existing else None

        # Prevent changes after payment, except for receipt
        if is_existing and old_invoice.date_paid is not None:
            changed_fields = {
                field.name: getattr(self, field.name)
                for field in self._meta.fields
                if field.name != 'receipt' and getattr(self, field.name) != getattr(old_invoice, field.name)
            }
            if changed_fields:
                raise Exception("Invoice cannot be modified because it has already been paid, except for the receipt.")

        super().save(*args, **kwargs)

        if self.date_paid is not None:
            from crm.utils import update_quote_invoices

            if self.invoice_type.type == InvoiceTypeEnum.DEPOSIT:
                update_quote_invoices(self.quote)

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
    external_id = models.CharField(unique=True, db_index=True, editable=False, max_length=255)
    text = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    text_from = models.CharField(max_length=15)
    text_to = models.CharField(max_length=15)
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

    def __str__(self):
        return self.external_id

    def get_lead(self):
        return Lead.objects.filter(phone_number=self.text_from).first() or Lead.objects.filter(phone_number=self.text_to).first()

    def user(self):
        return User.objects.filter(phone_number=self.text_from).first() or User.objects.filter(phone_number=self.text_to).first()
    
    def images(self):
        return self.media.filter(content_type__startswith="image/")

    def videos(self):
        return self.media.filter(content_type__startswith="video/")

    def audios(self):
        return self.media.filter(content_type__startswith="audio/")

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
    external_id = models.CharField(unique=True, db_index=True, editable=False, max_length=255)
    call_duration = models.IntegerField()
    date_created = models.DateTimeField(auto_now_add=True)
    call_from = models.CharField(max_length=15)
    call_to = models.CharField(max_length=15)
    is_inbound = models.BooleanField(default=False)
    recording_url = models.TextField(null=True)
    status = models.CharField(max_length=50)

    class Meta:
        db_table = "phone_call"

    def get_lead(self):
        from core.models import Lead
        return Lead.objects.filter(phone_number=self.call_from).first() or Lead.objects.filter(phone_number=self.call_to).first()

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_status = None

        if not is_new:
            try:
                old_status = PhoneCall.objects.get(pk=self.pk).status
            except PhoneCall.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if is_new or (old_status and old_status != self.status):
            entry = PhoneCallStatusHistory(
                phone_call=self,
                status=self.status
            )
            entry.save()

    def __str__(self):
        return self.external_id

class PhoneCallStatusHistory(models.Model):
    phone_call_status_history_id = models.AutoField(primary_key=True)
    phone_call = models.ForeignKey(PhoneCall, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Status {self.status} on {self.date_created}"

    class Meta:
        db_table = 'phone_call_status_history'

class PhoneCallTranscription(models.Model):
    phone_call_transcription_id = models.AutoField(primary_key=True)
    phone_call = models.OneToOneField(
        PhoneCall,
        on_delete=models.CASCADE,
        db_column='phone_call_id',
        related_name='transcription'
    )
    external_id = models.CharField(unique=True, db_index=True, editable=False, max_length=255)
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

class AdCampaign(models.Model):
    ad_campaign_id = models.BigIntegerField()
    name = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'ad_campaign'

class AdGroup(models.Model):
    ad_group_id = models.BigIntegerField()
    name = models.TextField()
    ad_campaign = models.ForeignKey(AdCampaign, related_name='ad_groups', db_column='ad_campaign_id', on_delete=models.RESTRICT)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'ad_group'
        unique_together = ('ad_group_id', 'ad_campaign_id')

class Ad(models.Model):
    ad_id = models.BigIntegerField()
    name = models.TextField(blank=True, null=True)
    ad_group = models.ForeignKey(AdGroup, related_name='ads', db_column='ad_group_id', on_delete=models.RESTRICT)
    platform_id = models.IntegerField(choices=AD_PLATFORMS)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'ad'
        unique_together = ('ad_id', 'platform_id')

class LeadMarketing(models.Model):
    lead_marketing_id = models.AutoField(primary_key=True)
    lead = models.OneToOneField(Lead, related_name='lead_marketing', db_column='lead_id', on_delete=models.CASCADE)
    source = models.CharField(max_length=255, null=True)
    medium = models.CharField(max_length=255, null=True)
    channel = models.CharField(max_length=255, null=True)
    landing_page = models.TextField(null=True)
    keyword = models.CharField(max_length=255, null=True)
    click_id = models.TextField(unique=True, null=True)
    client_id = models.TextField(unique=True, null=True)
    ip = models.GenericIPAddressField(null=True)
    external_id = models.UUIDField(unique=True, db_index=True, editable=False, null=True)
    user_agent = models.TextField(null=True)
    instant_form_lead_id = models.BigIntegerField(null=True, unique=True, db_index=True)
    instant_form_id = models.BigIntegerField(null=True)
    ad = models.ForeignKey(Ad, null=True, db_column='ad_id', on_delete=models.RESTRICT)

    referred_by = models.ForeignKey(
        'self',
        null=True,
        on_delete=models.SET_NULL,
        related_name='referrals'
    )

    def __str__(self):
        return f"Marketing info for Lead {self.lead.full_name}"
    
    def is_instant_form_lead(self):
        return bool(self.instant_form_lead_id)
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            Visit.objects.filter(external_id=self.external_id).update(lead_marketing=self)

    class Meta:
        db_table = 'lead_marketing'

class HTTPLog(models.Model):
    http_log_id = models.AutoField(primary_key=True)
    date_created = models.DateTimeField(default=timezone.now)
    method = models.CharField(max_length=10)
    url = models.TextField()
    query_params = models.JSONField(null=True, blank=True)
    payload = models.JSONField(null=True)
    headers = models.JSONField(null=True)
    response = models.JSONField(null=True, blank=True)
    status_code = models.IntegerField(null=True)
    error = models.JSONField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True)
    retries = models.IntegerField(default=0)
    service_name = models.CharField(max_length=100, null=True)

    def __str__(self):
        return f"[{self.service_name}] {self.method} {self.url} ({self.status_code})"

    class Meta:
        db_table = 'http_log'
        ordering = ["-date_created"]

class CallTrackingNumber(models.Model):
    call_tracking_number_id = models.AutoField(primary_key=True)
    phone_number = models.CharField(max_length=15, unique=True)
    forward_phone_number = models.CharField(max_length=15)
    date_expires = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.phone_number
    
    def is_free(self):
        return self.date_expires > timezone.now()

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
    date_assigned = models.DateTimeField(auto_now_add=True)
    date_expires = models.DateTimeField()
    metadata = models.JSONField(null=True)
    external_id = models.UUIDField(db_index=True, editable=False)

    def __str__(self):
        return str(self.call_tracking_number)
    
    def save(self, *args, **kwargs):
        expiry = timezone.now() + timedelta(minutes=settings.CALL_TRACKING_EXPIRATION_LIMIT)
        self.date_expires = expiry
        self.call_tracking_number.date_expires = expiry
        self.call_tracking_number.save()
        return super().save(*args, **kwargs)

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
    street_address_two = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=100, null=True)
    zip_code = models.CharField(max_length=20, null=True)
    special_instructions = models.TextField(null=True)
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
    
    @property
    def full_address(self):
        return f"{self.street_address}, {self.street_address_two}, {self.city}, {self.zip_code}, FL"

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
    external_id = models.UUIDField(editable=False)
    referrer = models.TextField(null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    url = models.TextField()
    session_duration = models.FloatField(default=0.0)
    
    lead_marketing = models.ForeignKey(LeadMarketing, null=True, on_delete=models.SET_NULL, related_name='visits')

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

class StoreItem(models.Model):
    store_item_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    image = models.ImageField(upload_to=save_image_path, null=True)
    product_quantity = models.FloatField(null=True)
    unit = models.ForeignKey(
        'Unit',
        db_column='unit_id',
        on_delete=models.RESTRICT,
        null=True
    )

    store = models.ForeignKey(
        Store,
        db_column='store_id',
        on_delete=models.RESTRICT
    )

    def __str__(self):
        return f'{self.name}'

    class Meta:
        db_table = 'store_item'

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
    from_unit = models.ForeignKey(
        Unit,
        db_column='from_unit',
        related_name='unit_conversions_from',
        on_delete=models.CASCADE
    )
    to_unit = models.ForeignKey(
        Unit,
        db_column='to_unit',
        related_name='unit_conversions_to',
        on_delete=models.CASCADE
    )
    multiplier = models.FloatField()

    def __str__(self):
        return f'{self.from_unit} to {self.to_unit}'

    class Meta:
        db_table = 'unit_conversion'

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
        db_column='ingredient_id',
        null=True,
        on_delete=models.SET_NULL
    )
    unit = models.ForeignKey(
        Unit,
        db_column='unit_id',
        null=True,
        on_delete=models.SET_NULL
    )
    amount = models.FloatField()

    class Meta:
        db_table = 'cocktail_ingredient'
        unique_together = ('cocktail', 'ingredient')

class EventShoppingList(models.Model):
    event_shopping_list_id = models.AutoField(primary_key=True)
    external_id = models.UUIDField(unique=True, db_index=True, default=uuid.uuid4, editable=False)

    event = models.OneToOneField(
        Event,
        related_name='shopping_list',
        db_column='event_id',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f'{self.event} Shopping List'

    class Meta:
        db_table = 'event_shopping_list'

class EventShoppingListEntry(models.Model):
    event_shopping_list_entry_id = models.AutoField(primary_key=True)
    quantity = models.FloatField()

    event_shopping_list = models.ForeignKey(
        EventShoppingList,
        related_name='entries',
        db_column='event_shopping_list_id',
        on_delete=models.CASCADE
    )

    store_item = models.ForeignKey(
        StoreItem,
        db_column='store_item_id',
        on_delete=models.CASCADE
    )

    unit = models.ForeignKey(
        Unit,
        db_column='unit_id',
        on_delete=models.RESTRICT
    )

    def __str__(self):
        return f'{self.store_item.name} ({self.quantity})'

    class Meta:
        db_table = 'event_shopping_list_entry'
        constraints = [
            models.UniqueConstraint(
                fields=['event_shopping_list', 'store_item'],
                name='unique_store_item_per_event_shopping_list'
            )
        ]

class QuotePreset(models.Model):
    quote_preset_id = models.AutoField(primary_key=True)
    services = models.ManyToManyField('core.Service', related_name='services', through='QuotePresetService')
    name = models.CharField(max_length=255)
    text_content = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'quote_preset'

class QuotePresetService(models.Model):
    quote_preset_service_id = models.AutoField(primary_key=True)
    quote_preset = models.ForeignKey(QuotePreset, db_column='quote_preset_id', on_delete=models.CASCADE)
    service = models.ForeignKey(Service, db_column='service_id', on_delete=models.RESTRICT)

    class Meta:
        db_table = 'quote_preset_service'
        constraints = [
            models.UniqueConstraint(
                fields=['quote_preset', 'service'],
                name='unique_quote_preset_service'
            )
        ]

class FacebookAccessToken(models.Model):
    facebook_access_token_id = models.AutoField(primary_key=True)
    access_token = models.TextField()
    date_expires = models.DateTimeField(default=timezone.now)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.access_token
    
    def is_expired(self) -> bool:
        return timezone.now() > self.date_expires

    @property
    def refresh_needed(self) -> bool:
        return self.is_expired() or self.date_expires - timezone.now() < timedelta(days=5)
    
    class Meta:
        db_table = 'facebook_access_token'

class GoogleAccessToken(models.Model):
    google_access_token_id = models.AutoField(primary_key=True)
    access_token = models.TextField()
    refresh_token = models.TextField()
    scope = models.TextField(blank=True, null=True)
    date_expires = models.DateTimeField(default=timezone.now)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.access_token

    def is_expired(self) -> bool:
        return timezone.now() > self.date_expires

    @property
    def refresh_needed(self) -> bool:
        return self.is_expired() or (self.date_expires - timezone.now()) < timedelta(days=5)

    class Meta:
        db_table = 'google_access_token'

class InternalLog(models.Model):
    LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]

    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    message = models.TextField()
    logger = models.CharField(max_length=255)
    date_created = models.DateTimeField(default=timezone.now)
    pathname = models.TextField(null=True)
    lineno = models.IntegerField(null=True)
    exception = models.TextField(null=True)

    def __str__(self):
        return f"[{self.date_created}] {self.level} - {self.message[:50]}"
    
    class Meta:
        db_table = 'internal_log'

class GoogleReview(models.Model):
    review_id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=255, unique=True)
    reviewer_display_name = models.CharField(max_length=255, null=True, blank=True)
    reviewer_profile_photo_url = models.URLField(null=True, blank=True)
    star_rating = models.CharField(max_length=20)
    rating_value = models.IntegerField()
    comment = models.TextField(null=True, blank=True)
    date_created = models.DateTimeField()
    date_updated = models.DateTimeField()
    location_id = models.CharField(max_length=255)
    should_show = models.BooleanField(default=False)

    class Meta:
        db_table = 'google_review'
        indexes = [
            models.Index(fields=["external_id"]),
            models.Index(fields=["location_id"]),
        ]
        ordering = ["-date_created"]

    def __str__(self):
        return self.reviewer_display_name or 'Anonymous'
    
    def clean(self):
        super().clean()

        if self.should_show:
            is_showing = GoogleReview.objects.filter(should_show=True)

            if self.pk:
                is_showing = is_showing.exclude(pk=self.pk)

            if is_showing.count() >= 8:
                raise ValidationError("Cannot exceeed more than 8 starred reviews.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)