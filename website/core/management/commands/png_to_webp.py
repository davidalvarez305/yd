import os
import tempfile
import boto3
from botocore.exceptions import ClientError
from PIL import Image
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Convert PNG files in S3 media/ folder to lossless WebP using Pillow'

    def add_arguments(self, parser):
        parser.add_argument(
            '--bucket',
            required=True,
            help='S3 bucket name',
        )
        parser.add_argument(
            '--prefix',
            default='media/',
            help='S3 prefix/folder to scan for PNG files (default: media/)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show files to convert without performing conversion',
        )

    def handle(self, *args, **options):
        bucket = options['bucket']
        prefix = options['prefix']
        dry_run = options['dry_run']

        s3 = boto3.client('s3')

        paginator = s3.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)

        png_files = []

        self.stdout.write(f"Scanning for PNG files in s3://{bucket}/{prefix}")

        for page in page_iterator:
            for obj in page.get('Contents', []):
                key = obj['Key']
                if key.lower().endswith('.png'):
                    png_files.append(key)

        if not png_files:
            self.stdout.write("No PNG files found.")
            return

        self.stdout.write(f"Found {len(png_files)} PNG files.")

        for key in png_files:
            webp_key = key[:-4] + '.webp'

            if dry_run:
                self.stdout.write(f"Would convert {key} -> {webp_key}")
                continue

            with tempfile.TemporaryDirectory() as tmpdir:
                png_path = os.path.join(tmpdir, 'input.png')
                webp_path = os.path.join(tmpdir, 'output.webp')

                self.stdout.write(f"Downloading {key}...")
                try:
                    s3.download_file(bucket, key, png_path)
                except ClientError as e:
                    self.stderr.write(f"Failed to download {key}: {e}")
                    continue

                self.stdout.write(f"Converting {key} to lossless WebP...")
                try:
                    with Image.open(png_path) as im:
                        im.save(webp_path, format='WEBP', quality=90, method=6)
                except Exception as e:
                    self.stderr.write(f"Failed to convert {key} to WebP: {e}")
                    continue

                self.stdout.write(f"Uploading {webp_key}...")
                try:
                    s3.upload_file(
                        webp_path,
                        bucket,
                        webp_key,
                        ExtraArgs={'ContentType': 'image/webp'}
                    )
                    self.stdout.write(f"✔ Converted and uploaded {webp_key}")
                except ClientError as e:
                    self.stderr.write(f"Failed to upload {webp_key}: {e}")
