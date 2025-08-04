import json
from django.dispatch import receiver
from django.db.models.signals import Signal
from django.db.models import Q
from django.utils.timezone import now

from core.conversions import conversion_service
from core.models import CallTrackingNumber, Lead, LeadMarketingMetadata, LeadStatusHistory

lead_status_changed = Signal()

def create_data_dict(lead: Lead, event_name=None, event=None):
    """
    Creates the data dictionary used to report marketing funnel events.
    """
    data = {
        'event_name': event_name,
        'ip_address': lead.lead_marketing.ip,
        'user_agent': lead.lead_marketing.user_agent,
        'instant_form_lead_id': lead.lead_marketing.instant_form_lead_id,
        'event_time': int(now().timestamp()),
        'phone_number': lead.phone_number,
        'external_id': str(lead.lead_marketing.external_id)
    }

    if event_name == 'event_booked' and event:
        data.update({
            'event_id': event.pk,
            'value': event.amount,
        })

    for metadata in lead.lead_marketing.metadata.all():
        if metadata.key == '_fbc':
            data['fbc'] = metadata.value
        elif metadata.key == '_fbp':
            data['fbp'] = metadata.value
        elif metadata.key == '_ga':
            data['ga'] = metadata.value
        elif metadata.key == 'gclid':
            data['gclid'] = metadata.value
        elif metadata.key == 'gbraid':
            data['gbraid'] = metadata.value
        elif metadata.key == 'wbraid':
            data['wbraid'] = metadata.value
        else:
            data[metadata.key] = metadata.value
        
    print(data)
    return data

@receiver(lead_status_changed)
def handle_lead_status_change(sender, instance: Lead, **kwargs):
    """
    This function is called when a lead status is saved.
    This function is used to report marketing funnel events.
    """
    from core.models import LeadMarketing, LeadStatusEnum, PhoneCall, CallTracking
    lead_marketing = LeadMarketing.objects.get(lead=instance)

    # Report Conversion Event
    status_event_map = {
        'LEAD_CREATED': 'generate_lead',
        'INVOICE_SENT': 'invoice_sent',
        'EVENT_BOOKED': 'event_booked',
    }

    event = kwargs.get('event')
    lead_status = instance.lead_status
    event_name = status_event_map.get(lead_status.status)

    if not event_name:
        return

    # Assign lead marketing data if lead came from phone call and the lead was just created
    if not lead_marketing.is_instant_form_lead() and lead_status.status == LeadStatusEnum.LEAD_CREATED:
        first_call = instance.phone_calls().order_by('date_created').first()
        if first_call:
            if first_call.is_inbound and first_call.date_created < instance.created_at:
                    call_tracking_number = CallTrackingNumber.objects.filter(phone_number=first_call.call_to).first()

                    if call_tracking_number:
                        tracking_call = (
                            CallTracking.objects
                            .filter(
                                call_tracking_number=call_tracking_number,
                                date_assigned__lt=first_call.date_created,
                                date_expires__gt=first_call.date_created,
                            )
                            .order_by('date_assigned')
                            .first()
                        )

                        if tracking_call and tracking_call.metadata:
                            marketing_data = tracking_call.metadata
                            if isinstance(marketing_data, str):
                                try:
                                    marketing_data = json.loads(marketing_data)
                                except json.JSONDecodeError:
                                    marketing_data = {}

                            if isinstance(marketing_data, dict):
                                model_fields = {f.name for f in LeadMarketing._meta.fields}

                                for key, value in marketing_data.items():
                                    if key in model_fields:
                                        setattr(lead_marketing, key, value)

                                lead_marketing.save()
                                
                                metadata = json.loads(marketing_data.metadata)

                                for key, value in metadata.items():
                                    entry = LeadMarketingMetadata(
                                        key=key,
                                        value=value,
                                        lead_marketing=lead_marketing,
                                    )
                                    entry.save()

    # Now that the marketing data has been assigned, generate the data dict and send conversion
    data = create_data_dict(instance, event_name, event)

    # Always send conversion for LEAD_CREATED and EVENT BOOKED
    if lead_status.status == LeadStatusEnum.LEAD_CREATED or lead_status.status == LeadStatusEnum.EVENT_BOOKED:
        conversion_service.send_conversion(data=data)
    
    # Only need to report invoice sent once
    if lead_status.status == LeadStatusEnum.INVOICE_SENT:
        count = LeadStatusHistory.objects.filter(lead_status=lead_status, lead=instance).count()
        if count == 1:
            conversion_service.send_conversion(data=data)