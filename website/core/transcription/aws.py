import json
import os

import requests
import boto3
import time

from website import settings
from core.models import Lead, LeadNote, PhoneCallTranscription, User
from core.ai import ai_agent

class AWSTranscriptionService:
    def __init__(self):
        self.client = boto3.client(
            "transcribe",
            region_name=settings.AWS_S3_REGION_NAME
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self.output_prefix = settings.TRANSCRIPTION_STORAGE_PREFIX
        self.cdn = settings.AWS_S3_CUSTOM_DOMAIN
    
    def _get_s3_media_uri(self, file_name):
        return "s3://" + self.bucket_name + "/audio/" + file_name + ".mp3"

    def transcribe_audio(self, transcription: PhoneCallTranscription) -> dict:
        self.client.start_transcription_job(
            TranscriptionJobName=transcription.external_id,
            Media={"MediaFileUri": self._get_s3_media_uri(transcription.external_id)},
            MediaFormat="mp3",
            IdentifyMultipleLanguages=True,
            LanguageOptions=["en-US", "es-US"],
            OutputBucketName=self.bucket_name,
            OutputKey=self.output_prefix + transcription.external_id + ".json",
        )
    
    def process_transcription(self, transcription: PhoneCallTranscription):
        response = self.client.get_transcription_job(TranscriptionJobName=transcription.external_id)
        transcription_job = response.get("TranscriptionJob", {})

        if transcription_job.get('TranscriptionJobStatus') == "FAILED":
            print("Transcription failed.")
            return

        transcript_url = transcription_job.get("Transcript", {}).get("TranscriptFileUri")
        if not transcript_url:
            print("Transcript URL not found in response.")
            return

        response = requests.get(transcript_url)

        if response.status_code != 200:
            print('Bad Response for Transcription URL: ', response.status_code)
            return

        data = response.json()

        results = data.get("results", {})

        transcript_text = results.get("transcripts", [{}])[0].get("transcript", "")

        if not transcript_text:
            return

        job = {
            "language": transcription_job.get("LanguageCode"),
            "transcript": transcript_text,
            "items": results.get("items", []),
            "speaker_labels": results.get("speaker_labels", {}),
        }

        transcription.job = json.dumps(job)
        transcription.text = transcript_text
        transcription.save()

        user_phone = transcription.phone_call.call_to if transcription.phone_call.is_inbound else transcription.phone_call.call_from
        user = User.objects.filter(phone_number=user_phone).first() or User.objects.filter(phone_number=settings.COMPANY_PHONE_NUMBER).first()

        lead_phone = transcription.phone_call.call_from if transcription.phone_call.is_inbound else transcription.phone_call.call_to
        lead = Lead.objects.filter(phone_number=lead_phone).first()

        if lead is not None:
            ctx = { 'lead': lead, 'transcription': transcription, 'user': user }
            note = ai_agent.summarize_phone_call(ctx=ctx)

            LeadNote.objects.create(
                note=note,
                lead=lead,
                user=user,
            )