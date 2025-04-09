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

@receiver(post_save, sender=CallTracking)
def handle_call_tracking_save(sender, instance, created, **kwargs):
    """
    This function is called when a CallTracking record is saved.
    It checks if the call_from (Lead phone number) and call_to (CallTracking number) match in the PhoneCall table.
    If a match is found, trigger the workflow.
    Also checks if the phone_call.date_created is within the call_tracking's date range.
    """
    if created:
        try:
            # Step 1: Get the lead's phone number and the tracking phone number
            lead_phone_number = instance.client_id  # Assuming client_id is the lead's phone number
            tracking_phone_number = instance.call_tracking_number.call_tracking_number
            call_tracking_date_created = instance.date_assigned  # Assuming date_assigned is when the tracking was created
            call_tracking_date_expires = instance.date_expires  # Assuming date_expires is the expiration time

            # Step 2: Query the PhoneCall table for matching records
            phone_call_match = PhoneCall.objects.filter(
                call_from=lead_phone_number,
                call_to=tracking_phone_number,
                date_created__lte=call_tracking_date_expires,  # Ensure the phone call was created before the tracking expiration
                date_created__gt=call_tracking_date_created  # Ensure the phone call was created after the tracking was assigned
            ).first()  # Get the first match if it exists
            
            if phone_call_match:
                # Step 3: Trigger the workflow (You can call a function here or perform some action)
                trigger_workflow(phone_call_match)

                # Log the match
                logger.info(f"Phone call match found for Lead {lead_phone_number} and CallTracking {tracking_phone_number}.")
        except Exception as e:
            logger.error(f"Error processing CallTracking save: {str(e)}")

class LandingPage(models.Model):
    landing_page_id = models.AutoField(primary_key=True)
    url = models.SlugField()
    template = models.CharField(max_length=255)

    def __str__(self):
        return str(self.url)

    class Meta:
        db_table = 'landing_page'