from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from website.crm.models import Quote

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

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number', 'forward_phone_number', 'username']

    objects = UserManager()

    class Meta:
        db_table = 'user'

    def __str__(self):
        return self.username


class LeadStatus(models.Model):
    lead_status_id = models.IntegerField(primary_key=True)
    status = models.CharField(max_length=100)

class LeadInterest(models.Model):
    lead_interest_id = models.IntegerField(primary_key=True)
    interest = models.CharField(max_length=100)

class NextAction(models.Model):
    next_action_id = models.IntegerField(primary_key=True)
    action = models.CharField(max_length=255)

class Lead(models.Model):
    lead_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15, unique=True)
    opt_in_text_messaging = models.BooleanField(default=True)
    created_at = models.DateTimeField()
    email = models.EmailField(null=True, unique=True)
    message = models.TextField(null=True)
    lead_status = models.ForeignKey(LeadStatus, related_name='lead_status', db_column='lead_status_id', on_delete=models.SET_NULL)
    lead_interest = models.ForeignKey(LeadInterest, related_name='lead_interest', db_column='lead_interest_id', on_delete=models.SET_NULL)

    def __str__(self):
        return self.full_name

    class Meta:
        db_table = 'lead'

class LeadNextAction(models.Model):
    lead_next_action_id = models.IntegerField(primary_key=True)
    next_action = models.ForeignKey(NextAction, related_name='next_action', db_column='next_action_id', on_delete=models.CASCADE)
    lead = models.ForeignKey(Lead, related_name='lead', db_column='lead_id', on_delete=models.CASCADE)
    action_date = models.DateTimeField()

class LeadMarketing(models.Model):
    lead_marketing_id = models.AutoField(primary_key=True)
    lead = models.ForeignKey(Lead, related_name='lead', db_column='lead_id', on_delete=models.CASCADE)
    source = models.CharField(max_length=255, null=True)
    medium = models.CharField(max_length=255, null=True)
    channel = models.CharField(max_length=255, null=True)
    landing_page = models.TextField(null=True)
    keyword = models.CharField(max_length=255, null=True)
    referrer = models.TextField(null=True)
    click_id = models.TextField(unique=True, null=True)
    client_id = models.TextField(unique=True, null=True)
    campaign_id = models.BigIntegerField(null=True)
    ad_campaign = models.CharField(max_length=255, null=True)
    ad_group_id = models.BigIntegerField(null=True)
    ad_group_name = models.CharField(max_length=255, null=True)
    ad_id = models.BigIntegerField(null=True)
    ad_headline = models.TextField(null=True)
    language = models.CharField(max_length=50, null=True)
    button_clicked = models.CharField(max_length=255, null=True)
    device_type = models.CharField(max_length=50, null=True)
    ip = models.GenericIPAddressField(null=True)
    external_id = models.TextField(unique=True, null=True)
    instant_form_lead_id = models.BigIntegerField(null=True)
    instant_form_id = models.BigIntegerField(null=True)
    instant_form_name = models.CharField(max_length=255, null=True)

    def __str__(self):
        return f"Marketing info for Lead {self.lead_id}"

    class Meta:
        db_table = 'lead_marketing'

class InvoiceType(models.Model):
    invoice_type_id = models.IntegerField(primary_key=True)
    type = models.CharField(max_length=100)
    amount_percentage = models.FloatField()

    class Meta:
        db_table = 'invoice_type'

class Invoice(models.Model):
    invoice_id = models.IntegerField(primary_key=True)
    quote = models.ForeignKey(Quote, related_name='quote', db_column='quote_id', on_delete=models.CASCADE)
    date_created = models.DateTimeField()
    date_paid = models.DateTimeField()
    due_date = models.DateTimeField()
    invoice_type = models.ForeignKey(InvoiceType, related_name='invoice_type', db_column='invoice_type_id', on_delete=models.RESTRICT)
    url = models.TextField(max_length=255)
    stripe_invoice_id = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'invoice'

class LeadNote(models.Model):
    lead_note_id = models.IntegerField(primary_key=True)
    note = models.TextField()
    lead = models.ForeignKey(Lead, related_name='lead', db_column='lead_id', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='user', db_column='added_by_user_id', on_delete=models.SET_NULL)
    date_added = models.DateTimeField()

    class Meta:
        db_table = 'lead_note'