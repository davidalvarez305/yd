import time
import boto3
from botocore.exceptions import ClientError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Recursively add Cache-Control headers to S3 files and optionally invalidate CloudFront cache'

    def add_arguments(self, parser):
        parser.add_argument(
            '--bucket',
            type=str,
            required=True,
            help='S3 bucket name',
        )
        parser.add_argument(
            '--cache-control',
            type=str,
            default='public, max-age=31536000, immutable',
            help='Cache-Control header value to apply',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which files would be updated without making changes',
        )
        parser.add_argument(
            '--distribution-id',
            type=str,
            required=False,
            help='CloudFront distribution ID to invalidate',
        )
        parser.add_argument(
            '--invalidate-paths',
            action='store_true',
            help='Invalidate changed CloudFront paths (requires --distribution-id)',
        )

    def handle(self, *args, **options):
        bucket = options['bucket']
        cache_control_value = options['cache_control']
        dry_run = options['dry_run']
        distribution_id = options.get('distribution_id')
        should_invalidate = options.get('invalidate_paths')

        s3 = boto3.client('s3')
        prefixes = ['static/', 'media/']
        updated_paths = []

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
                            updated_paths.append(f"/{key}")

                    except ClientError as e:
                        self.stderr.write(f"✖ Failed to update {key}: {e}")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete."))
            return

        self.stdout.write(self.style.SUCCESS(f"Finished updating {len(updated_paths)} files."))

        if should_invalidate and distribution_id:
            self.invalidate_cloudfront(distribution_id, updated_paths)
        elif should_invalidate:
            self.stderr.write("✖ Must provide --distribution-id to use --invalidate-paths")

    def invalidate_cloudfront(self, distribution_id, paths):
        MAX_PATHS = 1000
        if not paths:
            self.stdout.write("No paths to invalidate.")
            return

        client = boto3.client('cloudfront')

        caller_reference = str(time.time()).replace('.', '')

        batch = paths[:MAX_PATHS]

        self.stdout.write(self.style.NOTICE(
            f"Invalidating {len(batch)} path(s) in CloudFront distribution {distribution_id}"))

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
            self.stdout.write(self.style.SUCCESS(
                f"CloudFront invalidation created with ID: {invalidation_id}"))
        except client.exceptions.NoSuchDistribution:
            self.stderr.write(f"✖ CloudFront distribution '{distribution_id}' not found.")
        except Exception as e:
            self.stderr.write(f"✖ Failed to create CloudFront invalidation: {e}")