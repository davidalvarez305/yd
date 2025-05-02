from abc import ABC, abstractmethod
import json

from django.http import HttpRequest, HttpResponse
import requests
import boto3
import time

from website import settings
from .models import PhoneCallTranscription

class TranscriptionServiceInterface(ABC):
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

class TranscriptionServiceFactory:
    @staticmethod
    def get_service() -> AWSTranscriptionService:
        if settings.DEBUG:
            return TranscriptionServiceFactory._create_aws_transcription_service()
        return TranscriptionServiceFactory._create_aws_transcription_service()

    @staticmethod
    def _create_aws_transcription_service() -> AWSTranscriptionService:
        return AWSTranscriptionService(bucket_name=settings.AWS_STORAGE_BUCKET_NAME)

class TranscriptionService(TranscriptionServiceInterface):
    def __init__(self):
        self.service = TranscriptionServiceFactory.get_service()

    def handle_inbound_call(self, request: HttpRequest) -> HttpResponse:
        return self.service.handle_inbound_call(request)

    def handle_call_status(self, request: HttpRequest) -> HttpResponse:
        return self.service.handle_call_status(request)

    def handle_call_recording_callback(self, request: HttpRequest) -> HttpResponse:
        return self.service.handle_call_recording_callback(request)