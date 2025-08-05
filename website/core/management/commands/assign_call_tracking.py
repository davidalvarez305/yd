import json
from django.core.management.base import BaseCommand

from core.models import CallTracking, CallTrackingNumber, Lead, LeadMarketing, LeadMarketingMetadata, PhoneCall

class Command(BaseCommand):
    def handle(self, *args, **options):
        leads = Lead.objects.all()

        for lead in leads:
            first_call = lead.phone_calls().order_by('date_created').first()
            if first_call:
                if first_call.is_inbound and first_call.date_created < lead.created_at:
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
                                        setattr(lead.lead_marketing, key, value)

                                lead.lead_marketing.save()
                                
                                metadata = json.loads(marketing_data.get('metadata'))

                                for key, value in metadata.items():
                                    entry = LeadMarketingMetadata(
                                        key=key,
                                        value=value,
                                        lead_marketing=lead.lead_marketing,
                                    )
                                    entry.save()