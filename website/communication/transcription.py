from abc import ABC, abstractmethod

import requests
import boto3
import time
import uuid

from website import settings
from .models import PhoneCallTranscription

class TranscriptionService(ABC):
    @abstractmethod
    def transcribe_audio(self, uri: str) -> dict:
        """Transcribe from given uri and return dict."""
        pass

class AWSTranscriptionService:
    def __init__(self, bucket_name: str, output_prefix: str = "uploads/jobs/"):
        self.transcribe_client = boto3.client("transcribe")
        self.bucket_name = bucket_name
        self.output_prefix = output_prefix

    def transcribe_audio(self, transcription: PhoneCallTranscription) -> dict:
        self.transcribe_client.start_transcription_job(
            TranscriptionJobName=transcription.external_id,
            Media={"MediaFileUri": transcription.audio.url},
            MediaFormat="mp3",
            IdentifyMultipleLanguages=True,
            LanguageOptions=["en-US", "es-US"],
            OutputBucketName=self.bucket_name,
            OutputKey=self.output_prefix + transcription.external_id + ".json"
        )

        while True:
            response = self.transcribe_client.get_transcription_job(TranscriptionJobName=transcription.external_id)
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

        full_json = requests.get(transcript_url).json()
        raw_results = full_json.get("results", {})

        transcript_text = raw_results.get("transcripts", [{}])[0].get("transcript", "")

        job = {
            "language": job_info.get("LanguageCode"),
            "transcript": transcript_text,
            "items": raw_results.get("items", []),
            "speaker_labels": raw_results.get("speaker_labels", {}),
        }

        transcription.job = job
        transcription.text = transcript_text
        transcription.save()