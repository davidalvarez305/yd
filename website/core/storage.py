from mimetypes import guess_type
from storages.backends.s3boto3 import S3Boto3Storage

class MediaS3Storage(S3Boto3Storage):
    def get_object_parameters(self, name):
        content_type, _ = guess_type(name)
        content_type = content_type or "binary/octet-stream"

        return {
            "ContentType": content_type,
            "CacheControl": "public, max-age=31536000, immutable",
        }