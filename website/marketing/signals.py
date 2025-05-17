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

    data = {}
    data['event_name'] = status_event_map.get(instance.status)
    data['ip_address'] = lead.lead_marketing.ip
    data['user_agent'] = lead.lead_marketing.user_agent
    data['event_time'] = lead.created_at

    value = lead.value()
    if value > 0.0:
        data['value'] = value

    attributes = ['client_id', 'click_id', 'email', 'phone_number']
    for attr in attributes:
        value = getattr(lead.lead_marketing, attr, None)
        if value:
            data[attr] = value

    conversion_service.send_conservion(data=data)