import os
import time
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Upload local /static/ files to S3 with cache headers and optionally invalidate CloudFront'

    def add_arguments(self, parser):
        parser.add_argument('--bucket', type=str, required=True, help='S3 bucket name')
        parser.add_argument('--dry-run', action='store_true', help='Only show what would happen')
        parser.add_argument('--invalidate-paths', action='store_true', help='Invalidate CloudFront for updated files')

    def handle(self, *args, **options):
        bucket = options['bucket']
        dry_run = options['dry_run']
        invalidate = options.get('invalidate_paths')

        local_static_dir = os.path.abspath('./static')
        if not os.path.exists(local_static_dir):
            self.stderr.write(f"✖ Local static directory not found: {local_static_dir}")
            return

        distribution_id = getattr(settings, 'AWS_CLOUDFRONT_DISTRIBUTION_ID', None)
        if invalidate and not distribution_id:
            self.stderr.write("✖ AWS_CLOUDFRONT_DISTRIBUTION_ID not set in settings.py")
            return

        cache_control = 'public, max-age=31536000, immutable'
        s3 = boto3.client('s3')
        updated_paths = []

        self.stdout.write(self.style.NOTICE(f"Uploading from {local_static_dir} to s3://{bucket}/static/"))

        for dirpath, _, filenames in os.walk(local_static_dir):
            for filename in filenames:
                local_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(local_path, local_static_dir).replace("\\", "/")
                s3_key = f"static/{rel_path}"
                cloudfront_path = f"/{s3_key}"

                if dry_run:
                    self.stdout.write(f"Would upload {s3_key}")
                    updated_paths.append(cloudfront_path)
                    continue

                try:
                    content_type = self.guess_content_type(filename)
                    s3.upload_file(
                        Filename=local_path,
                        Bucket=bucket,
                        Key=s3_key,
                        ExtraArgs={
                            'ContentType': content_type,
                            'CacheControl': cache_control,
                        }
                    )
                    self.stdout.write(f"✔ Uploaded {s3_key}")
                    updated_paths.append(cloudfront_path)
                except ClientError as e:
                    self.stderr.write(f"✖ Failed to upload {s3_key}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Uploaded {len(updated_paths)} files."))

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete."))
            return

        if invalidate:
            self.invalidate_cloudfront(distribution_id, updated_paths)

    def invalidate_cloudfront(self, distribution_id, paths):
        MAX_PATHS = 1000
        if not paths:
            self.stdout.write("No paths to invalidate.")
            return

        client = boto3.client('cloudfront')
        caller_reference = str(time.time()).replace('.', '')

        batch = paths[:MAX_PATHS]
        self.stdout.write(self.style.NOTICE(
            f"Invalidating {len(batch)} CloudFront paths in distribution {distribution_id}"))

        try:
            response = client.create_invalidation(
                DistributionId=distribution_id,
                InvalidationBatch={
                    'Paths': {
                        'Quantity': len(batch),
                        'Items': batch
                    },
                    'CallerReference': caller_reference
                }
            )
            invalidation_id = response['Invalidation']['Id']
            self.stdout.write(self.style.SUCCESS(f"Invalidation created: {invalidation_id}"))
        except client.exceptions.NoSuchDistribution:
            self.stderr.write(f"✖ Distribution '{distribution_id}' not found.")
        except Exception as e:
            self.stderr.write(f"✖ CloudFront invalidation failed: {e}")

    def guess_content_type(self, filename):
        import mimetypes
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or 'binary/octet-stream'