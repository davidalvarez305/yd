from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import Lead, LeadStatus, LeadStatusEnum
from core.conversions import conversion_service

@receiver(post_save, sender=LeadStatus)
def handle_lead_status_change(sender, instance: LeadStatus, created, **kwargs) -> None:
    """
    This function is called when a lead status is saved.
    This function is used to report marketing funnel events.
    """
    if created:
        return
    
    status_event_map = {
        'Lead Created': 'generate_lead',
        'Qualified Lead': 'qualified_lead',
        'Sales Prospect': 'invoice_sent',
        'Event Booking': 'event_booked',
    }
    
    lead = Lead.objects.filter(lead_id=instance.lead_set.first()).first()
    data = { 
        'event_name': status_event_map.get(instance.status),
        'lead_ad_id': lead.lead_marketing.lead_ad_id,
     }

    if instance.status == LeadStatusEnum.LEAD_CREATED.value:
        conversion_service.send_conservion(data=data)
    
    elif instance.status == LeadStatusEnum.QUALIFIED_LEAD.value:
        pass

    elif instance.status == LeadStatusEnum.INVOICE_SENT.value:
        pass

    elif instance.status == LeadStatusEnum.EVENT_BOOKED.value:
        pass