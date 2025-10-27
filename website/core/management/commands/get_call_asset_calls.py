from django.core.management.base import BaseCommand, CommandError

from core.call_tracking import call_tracking_service
from core.models import Ad, Lead, LeadMarketingMetadata, TrackingPhoneCall, TrackingPhoneCallMetadata
from core.utils import normalize_phone_number
from core.conversions import conversion_service

from website import settings

class Command(BaseCommand):
    help = "Send a conversion event via the Google Ads conversion service using either a JSON string (--event) or file (--event_file)."

    def handle(self, *args, **options):
        try:
            data = call_tracking_service.get_calls()

            calls = data.get('calls')
            if not calls:
                raise ValueError(f"❌ No phone calls attribute in data.")

            for call in calls:
                id = call.get('id')
                gclid = call.get('gclid')
                keyword = call.get('keyword')
                tracking_phone_number = call.get('tracking_phone_number')

                if not gclid:
                    continue

                if normalize_phone_number(tracking_phone_number) != normalize_phone_number(settings.GOOGLE_ADS_CALL_ASSET_PHONE_NUMBER):
                    continue

                tracking_call = TrackingPhoneCall.objects.filter(external_id=id).first()
                if not tracking_call:
                    continue

                click_id = tracking_call.metadata.filter(key='gclid').first()
                if click_id:
                    continue

                TrackingPhoneCallMetadata.objects.create(
                    key='gclid',
                    value=gclid,
                    tracking_phone_call=tracking_call,
                )

                keyword_metadata = tracking_call.metadata.filter(key='keyword').first()
                if not keyword_metadata and keyword:
                    TrackingPhoneCallMetadata.objects.create(
                        key='keyword',
                        value=keyword,
                        tracking_phone_call=tracking_call,
                    )

                lead = Lead.objects.filter(phone_number=tracking_call.call_from).first()
                if not lead:
                    continue

                marketing_click_id = lead.lead_marketing.metadata.filter(key='gclid').first()
                if not marketing_click_id:
                    LeadMarketingMetadata.objects.create(
                        key='gclid',
                        value=gclid,
                        lead_marketing=lead.lead_marketing,
                    )

                    events = lead.events.all()

                    for event in events:
                        try:
                            gads_service = conversion_service.get("gads")

                            data = {
                                'event_name': 'event_booked',
                                'gclid': gclid,
                                'event_time': event.date_paid.timestamp(),
                                'value': event.amount,
                                'order_id': event.pk,
                            }

                            gads_service.send_conversion(data=data)
                        except Exception as e:
                            print(f'Error trying to send Google Ads conv: {e}')
                            continue

                if not lead.lead_marketing.ad:
                    ad = Ad.objects.filter(name=keyword).first()
                    if ad:
                        lead.lead_marketing.ad = ad
                        lead.lead_marketing.save()

        except Exception as e:
            raise CommandError(f"❌ Failed to send Google Ads conversion: {e}")