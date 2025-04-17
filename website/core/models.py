from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.db.models import Q

from communication.models import Message, PhoneCall

class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required")
        user = self.model(username=username, **extra_fields)
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

    events = models.ManyToManyField('crm.Event', related_name='staff', through='crm.EventStaff')

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number', 'forward_phone_number']

    objects = UserManager()

    class Meta:
        db_table = 'user'

    def __str__(self):
        return self.username


class LeadStatus(models.Model):
    lead_status_id = models.IntegerField(primary_key=True)
    status = models.CharField(max_length=100)

    def __str__(self):
        return self.status

class LeadInterest(models.Model):
    lead_interest_id = models.IntegerField(primary_key=True)
    interest = models.CharField(max_length=100)

    def __str__(self):
        return self.interest

class NextAction(models.Model):
    next_action_id = models.IntegerField(primary_key=True)
    action = models.CharField(max_length=255)

class Lead(models.Model):
    lead_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, unique=True)
    opt_in_text_messaging = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    email = models.EmailField(null=True, unique=True)
    message = models.TextField(null=True)
    lead_status = models.ForeignKey(LeadStatus, related_name='stauses', null=True, db_column='lead_status_id', on_delete=models.SET_NULL)
    lead_interest = models.ForeignKey(LeadInterest, db_column='lead_interest_id', null=True, on_delete=models.SET_NULL)
    actions = models.ManyToManyField('core.NextAction', related_name='actions', through='LeadNextAction')

    def __str__(self):
        return self.full_name
    
    def phone_calls(self):
        return PhoneCall.objects.filter(Q(call_from=self.phone_number) | Q(call_to=self.phone_number))
    
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
    
    class Meta:
        db_table = 'lead'

class LeadNextAction(models.Model):
    lead_next_action_id = models.IntegerField(primary_key=True)
    next_action = models.ForeignKey(NextAction, db_column='next_action_id', on_delete=models.CASCADE)
    lead = models.ForeignKey(Lead, db_column='lead_id', on_delete=models.CASCADE)
    action_date = models.DateTimeField()

class ServiceType(models.Model):
    service_type_id = models.IntegerField(primary_key=True)
    type = models.CharField(max_length=100)

    class Meta:
        db_table = 'service_type'

class UnitType(models.Model):
    unit_type_id = models.IntegerField(primary_key=True)
    type = models.CharField(max_length=100)

    class Meta:
        db_table = 'unit_type'

class Quote(models.Model):
    quote_id = models.IntegerField(primary_key=True)
    external_id = models.CharField(max_length=100)
    lead = models.ForeignKey(Lead, related_name='quotes', db_column='lead_id', on_delete=models.CASCADE)
    guests = models.IntegerField()
    hours = models.FloatField()
    event_date = models.DateTimeField()

    services = models.ManyToManyField('core.Service', related_name='quote_services', through='QuoteService')

    class Meta:
        db_table = 'quote'

class Service(models.Model):
    service_id = models.IntegerField(primary_key=True)
    service_type = models.ForeignKey(ServiceType, db_column='service_type_id', on_delete=models.RESTRICT)
    service = models.CharField(max_length=255)
    suggested_price = models.FloatField(null=True)
    guest_ratio = models.IntegerField(null=True)
    unit_type = models.ForeignKey(UnitType, db_column='unit_type_id', on_delete=models.RESTRICT)

    class Meta:
        db_table = 'service'

class QuoteService(models.Model):
    quote_service_id = models.IntegerField(primary_key=True)
    service = models.ForeignKey(Service, db_column='service_id', on_delete=models.RESTRICT)
    quote = models.ForeignKey(Quote, related_name='quote_services', db_column='quote_id', on_delete=models.RESTRICT)
    units = models.FloatField()
    price_per_unit = models.FloatField()

    class Meta:
        db_table = 'quote_service'

class InvoiceType(models.Model):
    invoice_type_id = models.IntegerField(primary_key=True)
    type = models.CharField(max_length=100)
    amount_percentage = models.FloatField()

    class Meta:
        db_table = 'invoice_type'

class Invoice(models.Model):
    invoice_id = models.IntegerField(primary_key=True)
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
    lead_note_id = models.IntegerField(primary_key=True)
    note = models.TextField()
    lead = models.ForeignKey(Lead, related_name='notes', db_column='lead_id', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='notes', db_column='added_by_user_id', on_delete=models.CASCADE)
    date_added = models.DateTimeField()

    class Meta:
        db_table = 'lead_note'