import json
import os
import uuid

from django.core.management.base import BaseCommand
from django.core.files import File

from website import settings
from core.call_tracking import call_tracking_service
from core.transcription import transcription_service
from core.models import (
    LandingPage,
    LandingPageConversion,
    Lead,
    LeadMarketingMetadata,
    PhoneCall,
    PhoneCallTranscription,
    SessionMapping,
    TrackingPhoneCall,
    TrackingPhoneCallMetadata,
)
from core.utils import cleanup_dir_files, download_file_from_url, get_session_data
from marketing.utils import create_ad_from_params, generate_params_dict_from_url


class Command(BaseCommand):
    help = "Get Instagram follower count via Facebook Graph API."

    def add_arguments(self, parser):
        parser.add_argument(
            "--id",
            type=str,
            required=True,
            help="CallRail Call ID",
        )

    def handle(self, *args, **options):
        call_id = options["id"]
        data = call_tracking_service.get_call_by_id(call_id=call_id)

        tracking_phone_call, _ = TrackingPhoneCall.objects.get_or_create(
            external_id=call_id,
            defaults={
                "call_duration": int(data.get("duration", 0)),
                "call_from": data.get("customer_phone_number"),
                "call_to": data.get("tracking_phone_number"),
                "status": data.get("call_type"),
            },
        )

        model_fields = {
            "resource_id",
            "duration",
            "customer_phone_number",
            "tracking_phone_number",
            "call_type",
        }

        lead = Lead.objects.get(phone_number=data.get("customer_phone_number"))

        for key, value in data.items():
            if key in model_fields:
                continue

            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            if value:
                TrackingPhoneCallMetadata.objects.update_or_create(
                    tracking_phone_call=tracking_phone_call,
                    key=key,
                    defaults={"value": value},
                )

        metadata = data.get("custom")
        if not metadata:
            return

        try:
            params = json.loads(metadata.value) or {}

            lp = params.get("calltrk_landing")
            if lp:
                params |= generate_params_dict_from_url(lp)

            external_id = params.get(settings.TRACKING_COOKIE_NAME)
            if external_id:
                session_mapping = SessionMapping.objects.filter(external_id=external_id).first()
                if session_mapping:
                    session = get_session_data(session_key=session_mapping.session_key)

                    lead.lead_marketing.ip = session.get("ip")
                    lead.lead_marketing.user_agent = session.get("user_agent")
                    lead.lead_marketing.external_id = external_id
                    lead.lead_marketing.ad = create_ad_from_params(params=params, cookies=metadata)
                    lead.lead_marketing.save()
                    lead.lead_marketing.assign_visits()

                    landing_page_id = session.get("landing_page_id")
                    if landing_page_id:
                        landing_page = LandingPage.objects.filter(pk=landing_page_id).first()
                        if landing_page:
                            LandingPageConversion.objects.create(
                                lead=lead,
                                landing_page=landing_page,
                                conversion_type=LandingPageConversion.PHONE_CALL,
                            )

            for key, value in params.items():
                if value:
                    LeadMarketingMetadata.objects.update_or_create(
                        lead_marketing=lead.lead_marketing,
                        key=key,
                        defaults={"value": value},
                    )

        except (TypeError, json.JSONDecodeError):
            self.stdout.write(self.style.ERROR("Failed to load params"))
        
        recording_url = data.get('recording')
        
        phone_call, _ = PhoneCall.objects.get_or_create(
            external_id=call_id,
            defaults={
                "call_duration": tracking_phone_call.call_duration,
                "date_created": tracking_phone_call.date_created,
                "call_from": tracking_phone_call.call_from,
                "call_to": tracking_phone_call.call_to,
                "is_inbound": True,
                "recording_url": recording_url,
                "status": tracking_phone_call.status,
            },
        )

        if not data.get('recording'):
            return
        
        has_transcription = PhoneCallTranscription.objects.filter(phone_call=phone_call).exists()

        if has_transcription:
            return

        job_name = str(uuid.uuid4())
        audio_filename = job_name + ".mp3"
        local_audio_path = os.path.join(settings.UPLOADS_URL, audio_filename)

        download_file_from_url(phone_call.recording_url, local_audio_path)

        try:
            with open(local_audio_path, 'rb') as audio_file:
                transcription = PhoneCallTranscription(
                    phone_call=phone_call,
                    external_id=job_name,
                    audio=File(audio_file, name=audio_filename)
                )
                transcription.save()

            transcription_service.transcribe_audio(transcription=transcription)

        finally:
            cleanup_dir_files(settings.UPLOADS_URL)