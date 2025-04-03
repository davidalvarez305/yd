from django.db import models
import json

class ConversionLog(models.Model):
    GOOGLE = 1
    FACEBOOK = 2
    SERVICE_TYPE_CHOICES = [
        (GOOGLE, "Google"),
        (FACEBOOK, "Facebook"),
    ]

    conversion_log_id = models.AutoField(primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    endpoint = models.URLField()
    payload = models.TextField()
    status_code = models.IntegerField()
    response = models.TextField(null=True)
    conversion_service_type_id = models.IntegerField(choices=SERVICE_TYPE_CHOICES)

    def __str__(self):
        return f"Conversion Log {self.conversion_log_id} - {self.date_created}"

    def save(self, *args, **kwargs):
        if isinstance(self.payload, dict):
            self.payload = json.dumps(self.payload)
        if isinstance(self.response, dict):
            self.response = json.dumps(self.response)
        super().save(*args, **kwargs)