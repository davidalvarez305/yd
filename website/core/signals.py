
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Lead
from website.communication.models import PhoneCall
from website.marketing.models import CallTracking, CallTrackingNumber

@receiver(post_save, sender=Lead)
def handle_lead_save(sender, instance, created, **kwargs):
    """
    This function is called when a lead record is saved.
    It checks if the call_from (lead phone number) and call_to (call tracking number) match in the phone call table.
    If there's a match, it assigns campaign-level data associated with that call tracking number to the marketing table & reports conv to appropriate ad platform.
    """
    if created:
        try:
            # Step 1: Get the lead's phone number and the tracking phone number
            lead_phone_number = sender.phone_number
            tracking_phone_number = instance.call_tracking_number.call_tracking_number
            call_tracking_date_created = instance.date_assigned
            call_tracking_date_expires = instance.date_expires

            # Step 2: Query the PhoneCall table for matching records
            phone_call_match = PhoneCall.objects.filter(
                call_from=lead_phone_number,
                call_to=tracking_phone_number,
                date_created__lte=call_tracking_date_expires,
                date_created__gt=call_tracking_date_created
            ).first()
            
            if phone_call_match:
                # Step 3: Trigger the workflow (You can call a function here or perform some action)
                trigger_workflow(phone_call_match)
                # Assign google or facebook campaign attribution
                # Report lead to google or facebook, where applicable
        except Exception as e:
            logger.error(f"Error processing CallTracking save: {str(e)}")