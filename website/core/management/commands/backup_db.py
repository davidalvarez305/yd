import os
import subprocess
import boto3
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

class Command(BaseCommand):
    help = "Dumps the local database and uploads it to AWS S3"

    def handle(self, *args, **options):
        db_name = settings.POSTGRES_DB
        db_user = settings.PGUSER
        db_password = settings.POSTGRES_PASSWORD
        db_host = settings.POSTGRES_HOST
        db_port = settings.POSTGRES_PORT

        s3_bucket = settings.AWS_STORAGE_BUCKET_NAME
        s3_key_prefix = "db_backups/"

        timestamp = timezone.now().strftime("%m_%d_%Y")
        file_name = f"{db_name}_{timestamp}.sql"
        sql_dump_path = os.path.join("/tmp", file_name)

        dump_cmd = [
            "pg_dump",
            "-h", db_host,
            "-U", db_user,
            "-d", db_name,
            "-p", str(db_port),
            "-f", sql_dump_path,
        ]

        env_vars = os.environ.copy()
        env_vars["PGPASSWORD"] = db_password

        self.stdout.write(f"📡 Running pg_dump for database {db_name}...")
        try:
            subprocess.run(dump_cmd, env=env_vars, check=True)
        except subprocess.CalledProcessError as e:
            raise CommandError(f"pg_dump failed: {e}")

        # Upload to S3
        s3_key = s3_key_prefix + file_name
        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        self.stdout.write(f"☁️ Uploading {sql_dump_path} to s3://{s3_bucket}/{s3_key} ...")
        try:
            s3.upload_file(sql_dump_path, s3_bucket, s3_key)
        except Exception as e:
            raise CommandError(f"S3 upload failed: {e}")

        os.remove(sql_dump_path)