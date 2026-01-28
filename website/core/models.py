from datetime import datetime, timedelta, date
from decimal import Decimal
from enum import Enum
from typing import Union
import uuid
from django.db import IntegrityError, models
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.utils import timezone
from django.db.models import Q, Sum
from website import settings
from core.utils import format_phone_number, generate_order_code, media_upload_path, save_image_path

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
    email = models.EmailField(default=settings.COMPANY_EMAIL)
    phone_number = models.CharField(max_length=20, unique=True)
    forward_phone_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    external_id = models.CharField(max_length=255, null=True, unique=True, db_index=True)

    events = models.ManyToManyField('Event', related_name='staff', through='EventStaff')

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email', 'phone_number', 'forward_phone_number']

    objects = UserManager()

    class Meta:
        db_table = 'user'

    def __str__(self):
        return self.first_name + " " + self.last_name

class UserRoleChoices(models.TextChoices):
    DRIVER = 'Driver'
    WAREHOUSE_STAFF = 'Warehouse Staff'

class UserRole(models.Model):
    user_role_id = models.AutoField(primary_key=True)
    role = models.CharField(max_length=60, choices=UserRoleChoices)
    user = models.ForeignKey(User, related_name='roles', db_column='user_id', on_delete=models.CASCADE)

    def __str__(self):
        return self.role

    class Meta:
        db_table = 'user_role'

class BusinessSegmentChoices(models.TextChoices):
    BARTENDING = 'Bartending'
    RENTALS = 'Rentals'

class BusinessSegment(models.Model):
    business_segment_id = models.AutoField(primary_key=True)
    segment = models.CharField(max_length=15, choices=BusinessSegmentChoices)

    def __str__(self):
        return self.segment
    
    class Meta:
        db_table = 'business_segment'

class LeadStatusEnum(Enum):
    LEAD_CREATED = 'LEAD_CREATED'
    INVOICE_SENT = 'INVOICE_SENT'
    EVENT_BOOKED = 'EVENT_BOOKED'
    RE_ENGAGED = 'RE_ENGAGED'
    ARCHIVED = 'ARCHIVED'

    def __str__(self):
        return self.value
    
    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)

class LeadStatusChoices(models.TextChoices):
    LEAD_CREATED = 'Lead Created'
    FIRST_TOUCH = 'First Touch'
    FIRST_RESPONSE = 'First Response'
    INVOICE_SENT = 'Invoice Sent'
    FIRST_FOLLOW_UP = 'FIRST_FOLLOW_UP', 'First Follow Up'
    SECOND_FOLLOW_UP = 'SECOND_FOLLOW_UP', 'Second Follow Up'
    EVENT_BOOKED = 'EVENT_BOOKED', 'Event Booked'
    ARCHIVED = 'ARCHIVED', 'Archived'

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
    lead_status = models.ForeignKey(LeadStatus, on_delete=models.RESTRICT)
    date_changed = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lead {self.lead.pk} - Status {self.lead_status.get_status_display()} on {self.date_changed}"

    class Meta:
        db_table = 'lead_status_history'

class LeadActivityChoices(models.TextChoices):
    WEBSITE_VISIT = 'website_visit'
    TEXT_SENT = 'text_sent'

class LeadActivity(models.Model):
    lead_activity_id = models.AutoField(primary_key=True)
    activity = models.CharField(max_length=255, choices=LeadActivityChoices.choices)

    def __str__(self):
        return self.activity

    class Meta:
        db_table = 'lead_activity'

class LeadActivityHistory(models.Model):
    lead_activity_history_id = models.AutoField(primary_key=True)
    lead_activity = models.ForeignKey(LeadActivity, db_column='lead_activity_id', on_delete=models.RESTRICT)
    lead = models.ForeignKey('Lead', db_column='lead_id', on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lead.full_name} - {self.lead_activity.activity} - {self.formatted_date_created}"

    @property
    def formatted_date_created(self):
        """
        Formatted like '10/7 - 5:24 PM'
        """
        return timezone.localtime(self.date_created).strftime("%#m/%#d - %#I:%M %p")

    class Meta:
        db_table = 'lead_activity_history'

class LeadTaskChoices(models.TextChoices):
    FISRT_FOLLOW_UP = 'First Follow Up'
    SECOND_FOLLOW_UP = 'Second Follow Up'

class LeadTask(models.Model):
    lead_task_id = models.AutoField(primary_key=True)
    task = models.CharField(max_length=60, choices=LeadTaskChoices.choices, unique=True)
    is_automated = models.BooleanField()
    during_work_hours = models.BooleanField(default=False)

    def __str__(self):
        return self.task

    class Meta:
        db_table = 'lead_task'

class LeadTaskHistory(models.Model):
    lead_task_history_id = models.AutoField(primary_key=True)
    lead_task = models.ForeignKey(LeadTask, db_column='lead_task_id', on_delete=models.RESTRICT)
    lead = models.ForeignKey('Lead', related_name='tasks', db_column='lead_id', on_delete=models.CASCADE)
    date_scheduled = models.DateTimeField(auto_now_add=True)
    date_completed = models.DateTimeField(null=True)

    def __str__(self):
        return f"{self.lead.full_name} - {self.lead_task.task} - {self.formatted_date_scheduled}"

    @property
    def formatted_date_scheduled(self):
        """
        Formatted like '10/7 - 5:24 PM'
        """
        return timezone.localtime(self.date_scheduled).strftime("%#m/%#d - %#I:%M %p")

    class Meta:
        db_table = 'lead_task_history'

class Lead(models.Model):
    lead_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=255, unique=True)
    opt_in_text_messaging = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    message = models.TextField(null=True)
    lead_status = models.ForeignKey(LeadStatus, null=True, db_column='lead_status_id', on_delete=models.SET_NULL)
    
    search_vector = SearchVectorField(null=True)

    def __str__(self):
        return self.full_name
    
    def has_gbraid(self):
        return (
            self.lead_marketing.metadata.filter(key="gbraid").exists()
            and not self.lead_marketing.metadata.filter(key="gclid").exists()
        )
    
    def has_gclid(self):
        return self.lead_marketing.metadata.filter(
            Q(key='gclid') | Q(key='_gcl_aw') | Q(key='gbraid') | Q(key='wbraid')
        ).exists()
    
    def has_fbc(self):
        return self.lead_marketing.metadata.filter(key='_fbc').exists()
    
    def formatted_number(self):
        return format_phone_number(self.phone_number)
    
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

        total = self.events.aggregate(total=Sum("amount"))["total"] or 0.0

        for referral in self.lead_marketing.referrals.all():
            total += referral.lead.value(visited=visited)

        return total

    @property
    def manager(self):
        from core.managers.lead import LeadStateManager
        return LeadStateManager(self)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.__class__.objects.filter(pk=self.pk).update(
            search_vector=SearchVector('full_name', 'phone_number')
        )
    
    class Meta:
        db_table = 'lead'

class ServiceBusinessSegment(models.Model):
    service_business_segment_id = models.AutoField(primary_key=True)
    service = models.ForeignKey('Service', on_delete=models.RESTRICT, db_column='service_id')
    business_segment = models.ForeignKey(BusinessSegment, related_name='services', on_delete=models.RESTRICT, db_column='business_segment')

    def __str__(self):
        return self.service.service + " - " + self.business_segment.segment

    class Meta:
        db_table = 'service_business_segment'

class ServiceType(models.Model):
    service_type_id = models.AutoField(primary_key=True)
    type = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.type

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
    adults = models.IntegerField()
    minors = models.IntegerField(null=True)
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
    
    @property
    def is_booked(self) -> bool:
        invoices = self.invoices.select_related('invoice_type')

        full_invoice = invoices.filter(invoice_type__type=InvoiceTypeEnum.FULL.value, date_paid__isnull=False).exists()
        if full_invoice:
            return True

        deposit_paid = invoices.filter(invoice_type__type=InvoiceTypeEnum.DEPOSIT.value, date_paid__isnull=False).exists()

        return deposit_paid
    
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
        invoices = self.invoices.select_related('invoice_type')

        full_invoice = invoices.filter(invoice_type__type=InvoiceTypeEnum.FULL.value, date_paid__isnull=False).exists()
        if full_invoice:
            return True

        deposit_paid = invoices.filter(invoice_type__type=InvoiceTypeEnum.DEPOSIT.value, date_paid__isnull=False).exists()
        remaining_paid = invoices.filter(invoice_type__type=InvoiceTypeEnum.REMAINING.value, date_paid__isnull=False).exists()

        return deposit_paid and remaining_paid
    
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
            raise Exception('Quote cannot be modified if it is already paid.')
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

class PriceAdjustment(models.Model):
    price_adjustment_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'price_adjustment'

class ServicePriceAdustment(models.Model):
    service_price_adjustment_id = models.AutoField(primary_key=True)
    service = models.ForeignKey(Service, db_column='service_id', on_delete=models.CASCADE)
    price_adjustment = models.ForeignKey(PriceAdjustment, db_column='price_adjusment_id', on_delete=models.CASCADE)
    factor = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.service} - {self.price_adjustment} - {self.factor}"

    class Meta:
        db_table = 'service_price_adjustment'

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
        if self.is_extend_service():
            return True
        
        if self.quote.is_paid_off():
            return False

        return True

    def save(self, *args, **kwargs):
        if not self.can_modify_quote():
            raise Exception('Cannot modify quote which is paid off')
        
        resp = super().save(*args, **kwargs)

        return resp

    def delete(self, *args, **kwargs):
        if not self.can_modify_quote():
            raise Exception('Cannot modify quote which is paid off')
        return super().delete(*args, **kwargs)

    class Meta:
        db_table = 'quote_service'

class AddedOrRemoveActionChoices(models.TextChoices):
    ADDED = 'Added', 'Added'
    REMOVED = 'Removed', 'Removed'

class QuoteServiceChangeHistory(models.Model):
    quote_change_history_id = models.AutoField(primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, db_column='user_id', on_delete=models.RESTRICT)
    quote = models.ForeignKey(Quote, db_column='quote_id', related_name='changes', on_delete=models.RESTRICT)
    service = models.ForeignKey(Service, db_column='service_id', on_delete=models.RESTRICT)
    action = models.CharField(max_length=10, choices=AddedOrRemoveActionChoices.choices)
    units = models.FloatField()
    price_per_unit = models.FloatField()

    def __str__(self):
        local_dt = timezone.localtime(self.date_created)
        formatted_date = local_dt.strftime("%b %d, %#I:%M %p")
        return f"{self.user.first_name} {self.action} {self.units} units @ ${self.price_per_unit} of {self.service.service} on {formatted_date}"

    class Meta:
        db_table = 'quote_service_change_history'

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
    text = models.TextField(null=True)
    date_created = models.DateTimeField(default=timezone.now)
    text_from = models.CharField(max_length=15)
    text_to = models.CharField(max_length=15)
    is_inbound = models.BooleanField(default=False)
    status = models.CharField(max_length=50)
    is_read = models.BooleanField(default=False)
    is_notified = models.BooleanField(default=False)

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
    parent_id = models.CharField(unique=True, null=True, db_index=True, max_length=255)
    call_duration = models.IntegerField()
    date_created = models.DateTimeField(default=timezone.now)
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
    audio = models.FileField(upload_to='audio/')
    text = models.TextField(null=True)
    job = models.JSONField(null=True)

    class Meta:
        db_table = "phone_call_transcription"

    def __str__(self):
        return self.external_id

class TrackingPhoneCall(models.Model):
    tracking_phone_call_id = models.AutoField(primary_key=True)
    external_id = models.CharField(unique=True, db_index=True, editable=False, max_length=255)
    call_duration = models.IntegerField()
    date_created = models.DateTimeField(default=timezone.now)
    call_from = models.CharField(max_length=15)
    call_to = models.CharField(max_length=15)
    status = models.CharField(max_length=50)

    class Meta:
        db_table = "tracking_phone_call"
    
class TrackingPhoneCallMetadata(models.Model):
    tracking_phone_call_metadata_id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=255)
    value = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    tracking_phone_call = models.ForeignKey(TrackingPhoneCall, related_name="metadata", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.key}: {self.value}"

    class Meta:
        db_table = "tracking_phone_call_metadata"
        constraints = [
            models.UniqueConstraint(
                fields=["tracking_phone_call", "key"],
                name="unique_tracking_phone_call_key"
            )
        ]

class TrackingTextMessage(models.Model):
    tracking_text_message_id = models.AutoField(primary_key=True)
    external_id = models.CharField(unique=True, db_index=True, max_length=255)
    message = models.TextField()
    text_from = models.CharField(max_length=15)
    text_to = models.CharField(max_length=15)
    date_created = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "tracking_text_message"

class TrackingTextMessageMetadata(models.Model):
    tracking_text_message_metadata_id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=255)
    value = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    tracking_text_message = models.ForeignKey(
        TrackingTextMessage, related_name="metadata", on_delete=models.CASCADE
    )

    class Meta:
        db_table = "tracking_text_message_metadata"
        constraints = [
            models.UniqueConstraint(
                fields=["tracking_text_message", "key"],
                name="unique_tracking_text_message_key",
            )
        ]

class AdPlatformChoices(models.TextChoices):
    GOOGLE = 'Google Ads'
    FACEBOOK = 'Facebook Ads'
    MICROSOFT = 'Microsoft Ads'

class AdPlatform(models.Model):
    ad_platform_id = models.AutoField(primary_key=True)
    platform = models.CharField(max_length=30, choices=AdPlatformChoices.choices)

    def __str__(self):
        return self.platform

    class Meta:
        db_table = 'ad_platform'

class AdPlatformParamKeyChoices(models.TextChoices):
    URL = 'url'
    COOKIE = 'cookie'

class AdPlatformParam(models.Model):
    ad_platform_param_id = models.AutoField(primary_key=True)
    ad_platform = models.ForeignKey(AdPlatform, related_name='params', db_column='ad_platform_id', on_delete=models.CASCADE)
    param = models.CharField(max_length=30)
    type = models.CharField(max_length=15, choices=AdPlatformParamKeyChoices.choices)

    def __str__(self):
        return self.param

    class Meta:
        db_table = 'ad_platform_param'

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
    ad_id = models.BigIntegerField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    ad_group = models.ForeignKey(AdGroup, related_name='ads', db_column='ad_group_id', on_delete=models.RESTRICT)
    ad_platform = models.ForeignKey(AdPlatform, related_name='ads', db_column='platform_id', on_delete=models.RESTRICT)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'ad'
        unique_together = ('ad_id', 'platform_id')

class AdSpend(models.Model):
    ad_spend_id = models.AutoField(primary_key=True)
    date = models.DateField(default=date.today)
    spend = models.FloatField()
    platform = models.ForeignKey(AdPlatform, related_name='spend', db_column='platform_id', on_delete=models.CASCADE)

    def __str__(self):
        return self.amount

    class Meta:
        db_table = 'ad_spend'

class LeadMarketing(models.Model):
    lead_marketing_id = models.AutoField(primary_key=True)
    lead = models.OneToOneField(Lead, related_name='lead_marketing', db_column='lead_id', on_delete=models.CASCADE)
    ip = models.GenericIPAddressField(null=True)
    external_id = models.UUIDField(unique=True, db_index=True, editable=False, null=True)
    user_agent = models.TextField(null=True)
    instant_form_lead_id = models.BigIntegerField(null=True, unique=True, db_index=True)
    instant_form_id = models.BigIntegerField(null=True)
    ad = models.ForeignKey(Ad, related_name='leads', null=True, db_column='ad_id', on_delete=models.RESTRICT)

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
            self.assign_visits()
    
    def assign_visits(self):
        Visit.objects.filter(external_id=self.external_id).update(lead_marketing=self)

    class Meta:
        db_table = 'lead_marketing'

class LeadMarketingMetadata(models.Model):
    lead_marketing_metadata_id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=255)
    value = models.TextField()
    date_created = models.DateTimeField(default=timezone.now)
    lead_marketing = models.ForeignKey(LeadMarketing, related_name='metadata', on_delete=models.CASCADE)

    def __str__(self):
        return self.key

    class Meta:
        db_table = 'lead_marketing_metadata'
        constraints = [
            models.UniqueConstraint(fields=['lead_marketing', 'key'], name='unique_lead_marketing_key')
        ]

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

    def __str__(self):
        return self.phone_number

    class Meta:
        db_table = 'call_tracking_number'

class Cocktail(models.Model):
    cocktail_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = 'cocktail'
    
    def __str__(self):
        return self.name

class Event(models.Model):
    event_id = models.AutoField(primary_key=True)
    external_id = models.UUIDField(unique=True, db_index=True, default=uuid.uuid4, editable=False)
    
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

    lead = models.ForeignKey(
        Lead,
        related_name='events',
        db_column='lead_id',
        on_delete=models.CASCADE
    )
    
    event_status = models.ForeignKey(
        'EventStatus',
        db_column='event_status_id',
        on_delete=models.RESTRICT,
        related_name='current_events',
        null=True,
    )

    cocktail = models.ManyToManyField(
        Cocktail,
        through='EventCocktail',
        related_name='events'
    )

    quote = models.ForeignKey(
        Quote,
        related_name='events',
        on_delete=models.CASCADE,
        null=True,
    )

    def __str__(self):
        return f"{self.lead.full_name} - ${self.amount:.2f}"
    
    @property
    def has_bartending(self):
        return self.quote.quote_services.filter(service__service='Bartender').exists()
    
    @property
    def full_address(self):
        parts = [self.street_address, self.street_address_two, self.city, self.zip_code, "FL"]
        return ", ".join(filter(None, parts))

    class Meta:
        db_table = 'event'

class EventDocument(models.Model):
    event_document_id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Event, related_name='documents', db_column='event_id', on_delete=models.CASCADE)
    document = models.FileField(upload_to='documents/')

    class Meta:
        db_table = 'event_document'

class EventStatusChoices(models.TextChoices):
    BOOKED = 'Booked', 'Booked'
    ONBOARDING = 'Onboarding', 'Onboarding'
    AWAITING_CLIENT_CONFIRMATION = 'Awaiting Client Confirmation', 'Awaiting Client Confirmation'
    CONFIRMED = 'Confirmed', 'Confirmed'
    AWAITING_STAFF_ASSIGNMENT = 'Awaiting Staff Assignment', 'Awaiting Staff Assignment'
    ONBOARDING_COMPLETED = 'Onboarding Completed', 'Onboarding Completed'
    IN_PROGRESS = 'In Progress', 'In Progress'
    EXTENDED = 'Extended', 'Extended'
    SERVICE_COMPLETED = 'Service Completed', 'Service Completed'

class EventStatus(models.Model):
    event_status_id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=60, choices=EventStatusChoices)

    class Meta:
        db_table = 'event_status'

class EventStatusHistory(models.Model):
    event_status_history_id = models.AutoField(primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    event_status = models.ForeignKey(EventStatus, db_column='event_status_id', on_delete=models.RESTRICT)
    event = models.ForeignKey(Event, db_column='event_id', related_name='statuses', on_delete=models.CASCADE)
    user = models.ForeignKey(User,  null=True, db_column='user_id', on_delete=models.RESTRICT)

    class Meta:
        db_table = 'event_status_history'

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

class TaskStatus(models.TextChoices):
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"

class EventTaskLog(models.Model):
    event_task_log_id = models.AutoField(primary_key=True)
    action = models.CharField(max_length=100, db_index=True)
    message = models.TextField(null=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True)
    duration_seconds = models.FloatField(null=True)
    triggered_by = models.CharField(max_length=50, default="cron")

    status = models.CharField(max_length=10, choices=TaskStatus.choices, default=TaskStatus.SUCCESS)
    event = models.ForeignKey(Event, related_name="task_logs", db_column="event_id", on_delete=models.CASCADE, null=True)

    class Meta:
        db_table = "event_task_log"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["status"]),
            models.Index(fields=["started_at"]),
        ]

    def mark_completed(self, success=True, message=None):
        self.finished_at = timezone.now()
        self.status = (self.TaskStatus.SUCCESS if success else self.TaskStatus.FAILED)
        self.message = message
        
        if self.started_at and self.finished_at:
            self.duration_seconds = (self.finished_at - self.started_at).total_seconds()
        
        self.save()

    def __str__(self):
        return f"{self.action} - [{self.status}] @ {self.started_at.strftime('%b %d, %#I:%M %p')}"

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

class LandingPage(models.Model):
    landing_page_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    template_name = models.CharField(max_length=255, unique=True)
    business_segment = models.ForeignKey(BusinessSegment, related_name='landing_pages', on_delete=models.RESTRICT, db_column='business_segment_id', null=True)
    url = models.SlugField(null=True)
    is_active = models.BooleanField(default=False)
    is_control = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
    def latest_tracking_number(self):
        return self.tracking_numbers.order_by('-date_assigned').first()
    
    class Meta:
        db_table = 'landing_page'
        constraints = [
            models.UniqueConstraint(
                fields=["is_active", "is_control"],
                condition=models.Q(is_active=True, is_control=True),
                name="unique_active_control_lp"
            )
        ]

class LandingPageTrackingNumber(models.Model):
    landing_page_phone_number_id = models.AutoField(primary_key=True)
    landing_page = models.ForeignKey(LandingPage, on_delete=models.RESTRICT, related_name="tracking_numbers")
    call_tracking_number = models.ForeignKey(CallTrackingNumber, on_delete=models.RESTRICT, related_name="tracking_numbers")
    date_assigned = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.landing_page + " - " + self.call_tracking_number
    
    class Meta:
        db_table = 'landing_page_tracking_number'

class ConversionTypeChoices(models.TextChoices):
    PHONE_CALL = "phone_call"
    FORM_SUBMISSION = "form_submission"
    INSTANT_FORM = 'instant_form'

class LandingPageConversion(models.Model):
    landing_page_conversion_id = models.AutoField(primary_key=True)
    landing_page = models.ForeignKey(LandingPage, on_delete=models.RESTRICT, related_name="conversions")
    lead = models.ForeignKey(Lead, on_delete=models.RESTRICT)
    conversion_type = models.CharField(max_length=30, choices=ConversionTypeChoices.choices, default=ConversionTypeChoices.FORM_SUBMISSION)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.lead.full_name} - {self.landing_page.name} ({self.date_created.strftime('%b, %d')})"
    
    class Meta:
        db_table = 'landing_page_conversion'

class Visit(models.Model):
    visit_id = models.AutoField(primary_key=True)
    external_id = models.UUIDField(editable=False)
    referrer = models.TextField(null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    url = models.TextField()
    session_duration = models.FloatField(default=0.0)
    cookies = models.JSONField(default=dict)
    
    lead_marketing = models.ForeignKey(LeadMarketing, null=True, on_delete=models.SET_NULL, related_name='visits')
    landing_page = models.ForeignKey(LandingPage, null=True, on_delete=models.RESTRICT, related_name='visits')

    def __str__(self):
        return f"Visit {self.visit_id} - {self.url} from {self.referrer}"

    class Meta:
        db_table = 'visit'
        ordering = ['-date_created']

class SessionMapping(models.Model):
    external_id = models.CharField(max_length=36, unique=True, db_index=True)
    session_key = models.CharField(max_length=40, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'session_mapping'

class ItemCategory(models.Model):
    item_category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, db_index=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'item_category'

class ItemStateChoices(models.TextChoices):
    RESERVED = 'Reserved', 'Reserved'
    RETURNED = 'Returned', 'Returned'
    PURCHASED = 'Purchased', 'Purchased'
    SOLD = 'Sold', 'Sold'
    DECOMMISSIONED = 'Decommissioned', 'Decommissioned'

class Item(models.Model):
    item_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    item_category = models.ForeignKey(ItemCategory, db_column='item_category_id', related_name='items', on_delete=models.CASCADE)
    price = models.FloatField()

    def __str__(self):
        return self.name
    
    @property
    def inventory(self):
        from core.managers.item import ItemInventoryManager
        return ItemInventoryManager(self)

    class Meta:
        db_table = 'item'

class ItemState(models.Model):
    item_state_id = models.AutoField(primary_key=True)
    state = models.CharField(max_length=25, choices=ItemStateChoices, unique=True)

    def __str__(self):
        return self.state

    class Meta:
        db_table = 'item_state'

class ItemStateChangeHistory(models.Model):
    item_state_change_history_id = models.BigAutoField(primary_key=True)
    item = models.ForeignKey(Item, related_name='state_changes', on_delete=models.CASCADE)
    order = models.ForeignKey('Order', null=True, on_delete=models.CASCADE)
    state = models.ForeignKey(ItemState, on_delete=models.RESTRICT)
    quantity = models.PositiveIntegerField()
    target_date = models.DateField()

    class Meta:
        db_table = 'item_state_change_history'
        ordering = ['target_date', 'item_state_change_history_id']
        indexes = [
            models.Index(fields=['item', 'target_date']),
        ]

class Order(models.Model):
    order_id = models.BigAutoField(primary_key=True)
    lead = models.ForeignKey(Lead, db_column='lead_id', related_name='orders', on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    code = models.CharField(max_length=8, unique=True, db_index=True)
    user = models.ForeignKey(User, db_column='user_id', related_name='orders', on_delete=models.RESTRICT, null=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    has_delivery = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            for _ in range(5):
                self.code = generate_order_code()
                try:
                    super().save(*args, **kwargs)
                    return
                except IntegrityError:
                    self.code = None
            raise RuntimeError("Could not generate a unique order code")
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.code
    
    @property
    def manager(self):
        from core.managers.order import OrderManager
        return OrderManager(self)
    
    @property
    def current_status(self):
        latest_change = (
            self.changes
            .select_related("status")
            .order_by("-date_created")
            .first()
        )
        return latest_change.status.status if latest_change else None
    
    @property
    def amount(self):
        items_total = sum(
            (Decimal(item.units) * Decimal(item.price_per_unit))
            for item in self.items.all()
        )

        services_total = sum(
            (Decimal(service.units) * Decimal(service.price_per_unit))
            for service in self.services.all()
        )

        return items_total + services_total

    class Meta:
        db_table = 'order'

class OrderContact(models.Model):
    order_contact_id = models.AutoField(primary_key=True)
    order = models.OneToOneField("Order", related_name="contact", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=32)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_contact"

class OrderBillingContact(models.Model):
    order_billing_contact_id = models.AutoField(primary_key=True)
    order = models.OneToOneField("Order", related_name="billing_contact", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=32)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_billing_contact"

class OrderItem(models.Model):
    order_item_id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Order, db_column='order_id', related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, db_column='item_id', on_delete=models.CASCADE)
    units = models.PositiveIntegerField()
    price_per_unit = models.FloatField()

    def __str__(self):
        return self.item
    
    @property
    def total(self):
        return self.units * self.price_per_unit

    class Meta:
        db_table = 'order_item'

class OrderService(models.Model):
    order_service_id = models.AutoField(primary_key=True)
    service = models.ForeignKey(Service, db_column='service_id', on_delete=models.RESTRICT)
    order = models.ForeignKey(Order, related_name='services', db_column='order_id', on_delete=models.CASCADE)
    units = models.FloatField()
    price_per_unit = models.FloatField()

    def __str__(self):
        return self.service.service
    
    @property
    def total(self):
        return self.units * self.price_per_unit
    
    class Meta:
        db_table = 'order_service'

class OrderServiceChangeHistory(models.Model):
    order_service_change_history_id = models.AutoField(primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, db_column='user_id', on_delete=models.RESTRICT)
    order = models.ForeignKey(Order, db_column='order_id', related_name='service_changes', on_delete=models.RESTRICT)
    service = models.ForeignKey(Service, db_column='service_id', on_delete=models.RESTRICT)
    action = models.CharField(max_length=10, choices=AddedOrRemoveActionChoices.choices)
    units = models.FloatField()
    price_per_unit = models.FloatField()

    def __str__(self):
        local_dt = timezone.localtime(self.date_created)
        formatted_date = local_dt.strftime("%b %d, %#I:%M %p")
        return f"{self.user.first_name} {self.action} {self.units} units @ ${self.price_per_unit} of {self.service.service} on {formatted_date}"

    class Meta:
        db_table = 'order_service_change_history'

class OrderItemChangeHistory(models.Model):
    order_item_change_history_id = models.AutoField(primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, db_column='user_id', on_delete=models.RESTRICT)
    order = models.ForeignKey(Order, db_column='order_id', related_name='item_changes', on_delete=models.RESTRICT)
    item = models.ForeignKey(Item, db_column='item_id', on_delete=models.RESTRICT)
    action = models.CharField(max_length=10, choices=AddedOrRemoveActionChoices.choices)
    units = models.PositiveIntegerField()
    price_per_unit = models.FloatField()

    def __str__(self):
        local_dt = timezone.localtime(self.date_created)
        formatted_date = local_dt.strftime("%b %d, %#I:%M %p")
        return f"{self.user.first_name} {self.action} {self.units} units @ ${self.price_per_unit} of {self.item} on {formatted_date}"

    class Meta:
        db_table = 'order_item_change_history'

class OrderStatusChoices(models.TextChoices):
    ORDER_PLACED = 'Order Placed'
    ORDER_CANCELLED = 'Order Cancelled'
    AWAITING_PREPARATION = 'Awaiting Preparation'
    READY_FOR_DISPATCH = 'Ready for Dispatch'
    DISPATCHED = 'Dispatched'
    FINALIZED = 'Finalized'

    # Delivery flow
    DELIVERY_FAILED = 'Delivery Failed'
    PENDING_REVIEW_OF_DELIVERY = 'Pending Review of Delivery'
    DELIVERED = 'Delivered'
    PENDING_PICK_UP = 'Pending Pick Up'
    PICKED_UP = 'Picked Up'

    # Pickup-only flow
    CUSTOMER_PICKED_UP = 'Customer Picked Up'
    PENDING_CUSTOMER_RETURN = 'Pending Customer Return'
    CUSTOMER_RETURNED = 'Customer Returned'

class OrderStatus(models.Model):
    order_status_id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=60, choices=OrderStatusChoices, unique=True)

    def __str__(self):
        return self.status

    class Meta:
        db_table = 'order_status'

class OrderStatusChangeHistory(models.Model):
    order_status_change_history_id = models.AutoField(primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey(Order, db_column='order_id', related_name='changes', on_delete=models.RESTRICT)
    status = models.ForeignKey(OrderStatus, db_column='order_status_id', on_delete=models.RESTRICT)
    user = models.ForeignKey(User, db_column='user_id', null=True, on_delete=models.RESTRICT)

    @property
    def previous_status(self):
        previous_change = (
            OrderStatusChangeHistory.objects
            .filter(
                order=self.order,
                date_created__lt=self.date_created,
            )
            .order_by('-date_created')
            .select_related('status')
            .first()
        )

        return previous_change.status if previous_change else None

    def __str__(self):
        local_dt = timezone.localtime(self.date_created)
        formatted_date = local_dt.strftime("%b %d, %#I:%M %p")

        prev = self.previous_status
        prev_label = prev.name if prev else "None"

        user_name = self.user.first_name if self.user else "System"

        return (
            f"{user_name} changed status from "
            f"{prev_label} to {self.status.name} on {formatted_date}"
        )

    class Meta:
        db_table = 'order_status_change_history'
        ordering = ['date_created']

class OrderTaskChoices(models.TextChoices):
    LOAD_ORDER_ITEMS = 'Load Order Items'
    PREPARE_PICKUP_ORDER_ITEMS = 'Prepare Pickup Order Items'
    UNLOAD_ORDER_ITEMS = 'Unload Order Items'

class OrderTaskChoice(models.Model):
    order_task_choice_id = models.AutoField(primary_key=True)
    task = models.CharField(max_length=30, choices=OrderTaskChoices)

    def __str__(self):
        return self.task
    
    class Meta:
        db_table = 'order_task_choice'

class OrderTask(models.Model):
    order_task_id = models.AutoField(primary_key=True)
    task = models.ForeignKey(OrderTaskChoice, related_name='orders', db_column='order_task_choice_id', on_delete=models.RESTRICT)
    order = models.ForeignKey(Order, related_name='tasks', db_column='order_id', on_delete=models.CASCADE)
    user = models.ForeignKey(User, db_column='user_id', related_name='tasks', on_delete=models.RESTRICT)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.task
    
    @property
    def manager(self):
        from core.managers.order_task import OrderTaskManager
        return OrderTaskManager(self)

    class Meta:
        db_table = 'order_task'

class OrderTaskStatusChoices(models.TextChoices):
    ASSIGNED = 'Assigned'
    IN_PROGRESS = 'In Progress'
    UNABLE_TO_COMPLETE = 'Unable To Complete'
    COMPLETED = 'Completed'

class OrderTaskStatus(models.Model):
    order_task_status_id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=30, choices=OrderTaskStatusChoices)

    def __str__(self):
        return self.status

    class Meta:
        db_table = 'order_task_status'

class OrderTaskStatusChangeHistory(models.Model):
    order_task_status_change_history_id = models.AutoField(primary_key=True)
    order_task = models.ForeignKey(OrderTask, db_column='order_task_id', on_delete=models.RESTRICT)
    date_created = models.DateTimeField(auto_now_add=True)
    order_task_status = models.ForeignKey(OrderTaskStatus, db_column='order_task_status_id', on_delete=models.RESTRICT)
    notes = models.TextField(null=True)

    def __str__(self):
        return self.task

    class Meta:
        db_table = 'order_task_status_change_history'

class DeliveryVehicle(models.Model):
    delivery_vehicle_id = models.AutoField(primary_key=True)
    truck_code = models.CharField(max_length=4, unique=True, db_index=True)
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.description

    class Meta:
        db_table = 'delivery_vehicle'

class DeliveryVehicleStatusChoices(models.TextChoices):
    ACTIVE = 'Active'
    ASSIGNED = 'Assigned'
    READY_FOR_DISPATCH = 'Ready For Dispatch'
    ON_THE_ROAD = 'On The Road'
    INACTIVE = 'Inactive'

class DeliveryVehicleStatus(models.Model):
    delivery_vehicle_status_id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=30, choices=DeliveryVehicleStatusChoices.choices)

    def __str__(self):
        return self.status

    class Meta:
        db_table = 'delivery_vehicle_status'

class DeliveryVehicleStatusChangeHistory(models.Model):
    delivery_vehicle_status_change_history_id = models.AutoField(primary_key=True)
    vehicle = models.ForeignKey(DeliveryVehicle, db_column='delivery_vehicle_id', related_name='statuses', on_delete=models.CASCADE)
    status = models.ForeignKey(DeliveryVehicleStatus, db_column='delivery_vehicle_status_id', on_delete=models.RESTRICT)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'delivery_vehicle_status_change_history'

class DeliveryTruckDriverAssignment(models.Model):
    delivery_truck_driver_assignment_id = models.AutoField(primary_key=True)
    vehicle = models.ForeignKey(DeliveryVehicle, db_column='delivery_vehicle_id', related_name='assignments', on_delete=models.RESTRICT)
    driver = models.ForeignKey(User, db_column='user_id', on_delete=models.RESTRICT)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'delivery_truck_driver_assignment'

class State(models.Model):
    state_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    state_code = models.CharField(max_length=2)

    def __str__(self):
        return self.state_code

    class Meta:
        db_table = 'state'

class City(models.Model):
    city_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    state = models.ForeignKey(State, related_name='cities', db_column='state_id', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'city'

class ZipCode(models.Model):
    zip_code = models.CharField(max_length=10, primary_key=True, unique=True, db_index=True)
    city = models.ForeignKey(City, related_name='zip_codes', db_column='city_id', on_delete=models.CASCADE)

    class Meta:
        db_table = 'zip_code'

class Address(models.Model):
    address_id = models.AutoField(primary_key=True)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    zip_code = models.ForeignKey(ZipCode, related_name='addresses', db_column='zip_code', on_delete=models.CASCADE)

    class Meta:
        db_table = 'address'
        constraints = [
            models.UniqueConstraint(
                fields=["address_line_1", "address_line_2", "zip_code"],
                name="unique_address_per_zip"
            )
        ]

class RouteZone(models.Model):
    route_zone_id = models.AutoField(primary_key=True)
    zip_code = models.ForeignKey(ZipCode, related_name='zip_codes', db_column='zip_code', on_delete=models.CASCADE)
    delivery_fee = models.FloatField()

    class Meta:
        db_table = 'route_zone'

class OrderAddressTypeChoices(models.TextChoices):
    DELIVERY = 'Delivery', 'Delivery'
    PICKUP = 'Pickup', 'Pickup'

class OrderAddressTimeWindowTypeChoices(models.TextChoices):
    EXACT = 'Exact', 'Exact Time'
    FLEX = 'Flex', 'Flexible (4-hour window)'

class OrderAddress(models.Model):
    order_address_id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, related_name='addresses', db_column='order_id', on_delete=models.CASCADE)
    address = models.ForeignKey(Address, db_column='address_id', on_delete=models.RESTRICT)
    stop_type = models.CharField(max_length=60, choices=OrderAddressTypeChoices.choices)
    time_window = models.CharField(max_length=60, choices=OrderAddressTimeWindowTypeChoices.choices)
    contact_name = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=30)
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)

    class Meta:
        db_table = 'order_address'

class DriverRoute(models.Model):
    driver_route_id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=255, unique=True, db_index=True)
    driver = models.ForeignKey(User, related_name='driver_routes', on_delete=models.RESTRICT)
    vehicle = models.ForeignKey(DeliveryVehicle, related_name='routes', on_delete=models.RESTRICT)
    target_date = models.DateField()
    route_zone = models.ForeignKey(RouteZone, related_name='driver_routes', on_delete=models.RESTRICT)

    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'driver_route'
        constraints = [
            models.UniqueConstraint(
                fields=['driver', 'target_date'],
                name='unique_driver_per_date'
            ),
            models.UniqueConstraint(
                fields=['vehicle', 'target_date'],
                name='unique_vehicle_per_date'
            ),
        ]

class DriverStop(models.Model):
    driver_stop_id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=255, unique=True, null=True, db_index=True)
    driver_route = models.ForeignKey(DriverRoute, related_name='stops', on_delete=models.CASCADE)
    order_address = models.OneToOneField(OrderAddress, on_delete=models.CASCADE, db_column='order_address_id')
    web_tracking_link = models.TextField(null=True)

    def __str__(self):
        return f"{self.stop_type} for Order {self.order.code}"

    class Meta:
        db_table = 'driver_stop'

class DriverStopImage(models.Model):
    driver_stop_image_id = models.AutoField(primary_key=True)
    driver_stop = models.ForeignKey(DriverStop, related_name="images", on_delete=models.CASCADE)
    content_type = models.CharField(max_length=100)
    file = models.FileField(upload_to=media_upload_path)

    class Meta:
        db_table = "driver_stop_image"

    def __str__(self):
        return f"{self.content_type} - {self.file.name}"

    def is_image(self):
        return self.content_type.startswith("image/")

    def is_video(self):
        return self.content_type.startswith("video/")

    @property
    def media_type(self):
        if self.content_type.startswith("image/"):
            return "image"
        elif self.content_type.startswith("video/"):
            return "video"
        return "other"
    
class DriverStopStatusChoices(models.TextChoices):
    ALLOCATED = 'Allocated', 'Allocated'
    OUT_FOR_DELIVERY = 'Out For Delivery', 'Out For Delivery'
    COMPLETED = 'Completed', 'Completed'
    DELIVERY_FAILED = 'Delivery Failed', 'Delivery Failed'

class DriverStopStatus(models.Model):
    driver_stop_status_id = models.AutoField(primary_key=True)
    status = models.CharField(max_length=60, choices=DriverStopStatusChoices)

    def __str__(self):
        return self.status

    class Meta:
        db_table = 'driver_stop_status'

class DriverStopStatusChangeHistory(models.Model):
    driver_stop_status_change_history_id = models.AutoField(primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    driver_stop = models.ForeignKey(DriverStop, db_column='driver_stop_id', related_name='status_changes', on_delete=models.CASCADE)
    driver_stop_status = models.ForeignKey(DriverStopStatus, db_column='driver_stop_status_id', on_delete=models.RESTRICT)

    def __str__(self):
        local_dt = timezone.localtime(self.date_created)
        formatted_date = local_dt.strftime("%b %d, %#I:%M %p")
        return f"{self.status} - {formatted_date}"

    class Meta:
        db_table = 'driver_stop_status_change_history'
        ordering = ['-date_created']