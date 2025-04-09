from django.db import models
import json

class ConversionLog(models.Model):
    GOOGLE = 1
    FACEBOOK = 2
    SERVICE_TYPE_CHOICES = [
        (GOOGLE, "Google"),
        (FACEBOOK, "Facebook"),
    ]

    conversion_log_id = models.AutoField(primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    endpoint = models.URLField()
    payload = models.TextField()
    status_code = models.IntegerField()
    response = models.TextField(null=True)
    conversion_service_type_id = models.IntegerField(choices=SERVICE_TYPE_CHOICES)

    def __str__(self):
        return f"Conversion Log {self.conversion_log_id} - {self.date_created}"

    def save(self, *args, **kwargs):
        if isinstance(self.payload, dict):
            self.payload = json.dumps(self.payload)
        if isinstance(self.response, dict):
            self.response = json.dumps(self.response)
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'marketing_conversion_log'

class CallTrackingNumber(models.Model):
    GOOGLE = 1
    FACEBOOK = 2
    AD_PLATFORM_CHOICES = [
        (GOOGLE, "Google"),
        (FACEBOOK, "Facebook"),
    ]

    call_tracking_number_id = models.AutoField(primary_key=True)
    platform_id = models.IntegerField(choices=AD_PLATFORM_CHOICES)
    call_tracking_number = models.CharField(max_length=15)

    def __str__(self):
        return self.call_tracking_number

    class Meta:
        db_table = 'marketing_call_tracking_number'

class CallTracking(models.Model):
    call_tracking_id = models.AutoField(primary_key=True)
    call_tracking_number = models.ForeignKey(
        CallTrackingNumber,
        on_delete=models.CASCADE,
        db_column='call_tracking_number_id',
        related_name='call_trackings'
    )
    date_assigned = models.DateTimeField()
    date_expires = models.DateTimeField()
    client_id = models.TextField()
    click_id = models.TextField()

    def __str__(self):
        return str(self.call_tracking_number)

    class Meta:
        db_table = 'marketing_call_tracking'

class LandingPage(models.Model):
    landing_page_id = models.AutoField(primary_key=True)
    url = models.SlugField()
    template = models.CharField(max_length=255)

    def __str__(self):
        return str(self.url)

    class Meta:
        db_table = 'landing_page'