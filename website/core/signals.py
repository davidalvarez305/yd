from django.db.models.signals import post_save
from django.dispatch import receiver

from marketing.enums import ConversionEventType
from .models import Lead, PhoneCall
from core.models import CallTracking
from core.conversions import conversion_service_loader

@receiver(post_save, sender=Lead)
def handle_lead_save(sender, instance: Lead, created, **kwargs) -> None:
    """
    This function is called when a lead record is saved.
    It checks if the call_from (lead phone number) and call_to (call tracking number) match in the phone call table.
    If there's a match, it assigns campaign-level data associated with that call tracking number to the marketing table & reports conversion to appropriate ad platform.
    """
    if created:
        try:
            if instance.lead_marketing.is_instant_form_lead():
                return

            conversion_event_type = ConversionEventType.FormSubmission

            phone_call = PhoneCall.objects.filter(call_from=instance.phone_number, date_created__lt=instance.created_at).first()

            if phone_call:
                tracking_call = CallTracking.objects.filter(phone_number=phone_call.call_to).first()

                if tracking_call:
                    if phone_call.date_created <= tracking_call.date_expires:

                        marketing = instance.lead_marketing.first()
                        if marketing:
                            marketing.click_id = tracking_call.click_id
                            marketing.client_id = tracking_call.client_id
                            marketing.marketing_campaign = tracking_call.call_tracking_number.marketing_campaign
                            marketing.save()

                            conversion_event_type = ConversionEventType.WebsiteCall

            conversion_service_loader(conversion_event_type=conversion_event_type, lead=instance)
        except Exception as e:
            print(f"Error processing lead save: {str(e)}")