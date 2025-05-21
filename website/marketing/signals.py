from django.db.models.signals import Signal
from django.dispatch import receiver

from core.conversions import conversion_service

lead_status_changed = Signal()

@receiver(lead_status_changed)
def handle_lead_status_change(sender, instance, **kwargs):
    """
    This function is called when a lead status is saved.
    This function is used to report marketing funnel events.
    """
    status_event_map = {
        'Lead Created': 'generate_lead',
        'Qualified Lead': 'qualified_lead',
        'Sales Prospect': 'invoice_sent',
        'Event Booking': 'event_booked',
    }

    event_name = status_event_map.get(instance.lead_status.status)

    if not event_name:
        raise ValueError('Invalid event name from lead status.')
    
    data = {}
    data['event_name'] = event_name
    data['ip_address'] = instance.lead_marketing.ip
    data['user_agent'] = instance.lead_marketing.user_agent
    data['event_time'] = instance.created_at

    value = instance.value()
    if value > 0.0:
        data['value'] = value
        data['currency'] = 'USD'

    attributes = ['client_id', 'click_id', 'email', 'phone_number']
    for attr in attributes:
        value = getattr(instance.lead_marketing, attr, None)
        if value:
            data[attr] = value

    conversion_service.send_conservion(data=data)