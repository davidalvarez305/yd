import boto3
from botocore.exceptions import ClientError

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Recursively add Cache-Control headers to existing S3 files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--bucket',
            type=str,
            required=True,
            help='S3 bucket name (required)',
        )
        parser.add_argument(
            '--prefix',
            type=str,
            default='',
            help='S3 key prefix to target (e.g. "static/")',
        )
        parser.add_argument(
            '--cache-control',
            type=str,
            default='public, max-age=31536000, immutable',
            help='Cache-Control value to apply (default: public, max-age=31536000, immutable)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which files would be updated without making changes',
        )

    def handle(self, *args, **options):
        bucket = options.get('bucket')
        cache_control_value = options.get('cache_control')
        dry_run = options.get('dry_run')

        s3 = boto3.client('s3')
        prefixes = ['static/', 'media/']
        updated = 0

        for prefix in prefixes:
            self.stdout.write(self.style.NOTICE(f"Scanning s3://{bucket}/{prefix}"))

            paginator = s3.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)

            for page in page_iterator:
                for obj in page.get('Contents', []):
                    key = obj['Key']

                    if key.endswith('/'):
                        continue  # skip folders

                    try:
                        head = s3.head_object(Bucket=bucket, Key=key)
                        content_type = head.get('ContentType', 'binary/octet-stream')

                        if dry_run:
                            self.stdout.write(f"Would update {key}")
                        else:
                            s3.copy_object(
                                Bucket=bucket,
                                Key=key,
                                CopySource={'Bucket': bucket, 'Key': key},
                                MetadataDirective='REPLACE',
                                ContentType=content_type,
                                CacheControl=cache_control_value,
                            )
                            self.stdout.write(f"✔ Updated {key}")
                            updated += 1

                    except ClientError as e:
                        self.stderr.write(f"✖ Failed to update {key}: {e}")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Done. Updated {updated} files."))