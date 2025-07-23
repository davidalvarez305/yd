import json

import requests
import boto3
import time

from website import settings
from core.models import PhoneCallTranscription

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
            OutputKey=self.output_prefix + transcription.external_id + ".json"
        )

        while True:
            response = self.client.get_transcription_job(TranscriptionJobName=transcription.external_id)
            job_info = response.get("TranscriptionJob", {})
            status = job_info.get("TranscriptionJobStatus")

            if status in ("COMPLETED", "FAILED"):
                break
            time.sleep(5)

        if status == "FAILED":
            raise Exception(f"Transcription failed: {job_info.get('FailureReason', 'Unknown error')}")

        transcript_url = job_info.get("Transcript", {}).get("TranscriptFileUri")
        if not transcript_url:
            raise Exception("Transcript URL not found in response.")

        response = requests.get(transcript_url)
        response.raise_for_status()
        full_json = response.json()

        raw_results = full_json.get("results", {})

        transcript_text = raw_results.get("transcripts", [{}])[0].get("transcript", "")

        job = {
            "language": job_info.get("LanguageCode"),
            "transcript": transcript_text,
            "items": raw_results.get("items", []),
            "speaker_labels": raw_results.get("speaker_labels", {}),
        }

        transcription.job = json.dumps(job)
        transcription.text = transcript_text
        transcription.save()