from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Lead, PhoneCall
from core.models import CallTracking

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
            
            phone_call = (
                PhoneCall.objects
                .filter(
                    call_from=instance.phone_number,
                    date_created__lt=instance.created_at,
                )
                .order_by('-date_created')
                .first()
            )

            if not phone_call:
                return
           
            tracking_call = (
                CallTracking.objects
                .filter(
                    phone_number=phone_call.call_to,
                    date_assigned__lt=phone_call.date_created,
                    date_expires__gt=phone_call.date_created,
                )
                .order_by('-date_created')
                .first()
            )

            if not tracking_call:
                return

            marketing = getattr(instance, 'lead_marketing', None)
            if not marketing:
                return
            
            for key, value in tracking_call.metadata.items():
                if hasattr(marketing, key):
                    setattr(marketing, key, value)

            marketing.save()

        except Exception as e:
            print(f"Error processing lead save: {str(e)}")