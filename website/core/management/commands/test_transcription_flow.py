import uuid
import boto3
from django.core.management.base import BaseCommand
from website import settings

class Command(BaseCommand):
    help = "Set up AWS SNS topic and IAM role for AWS Transcribe job notifications"

    def handle(self, *args, **options):
        client = boto3.client(
            "transcribe",
            region_name=settings.AWS_S3_REGION_NAME
        )

        external_id = str(uuid.uuid4())
        uri = 's3://ydcocktails/audio/403a8a95-c3d2-4886-8c45-c435e58bb80c.mp3'

        client.start_transcription_job(
            TranscriptionJobName=external_id,
            Media={"MediaFileUri": uri},
            MediaFormat="mp3",
            IdentifyMultipleLanguages=True,
            LanguageOptions=["en-US", "es-US"],
            OutputBucketName=settings.AWS_STORAGE_BUCKET_NAME,
            OutputKey=settings.TRANSCRIPTION_STORAGE_PREFIX + external_id + ".json",
        )