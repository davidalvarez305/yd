import os
from django.db import models

class Message(models.Model):
    message_id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=255, unique=True)
    text = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    text_from = models.CharField(max_length=10)
    text_to = models.CharField(max_length=10)
    is_inbound = models.BooleanField(default=False)
    status = models.CharField(max_length=50)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = "message"

    def save(self, *args, **kwargs):
        self.text_from = self.text_from[-10:]
        self.text_to = self.text_to[-10:]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.external_id

    def get_lead(self):
        from core.models import Lead
        return Lead.objects.filter(phone_number=self.text_from).first() or Lead.objects.filter(phone_number=self.text_to).first()

    def images(self):
        return self.media.filter(content_type__startswith="image/")

    def videos(self):
        return self.media.filter(content_type__startswith="video/")

    def audios(self):
        return self.media.filter(content_type__startswith="audio/")

def media_upload_path(instance, filename):
    if instance.content_type.startswith("image/"):
        subdir = "images"
    elif instance.content_type.startswith("audio/"):
        subdir = "audio"
    elif instance.content_type.startswith("video/"):
        subdir = "videos"
    else:
        subdir = "other"

    return os.path.join("uploads", subdir, filename)

class MessageMedia(models.Model):
    message_media_id = models.AutoField(primary_key=True)
    message = models.ForeignKey("Message", related_name="media", on_delete=models.CASCADE)
    content_type = models.CharField(max_length=100)
    file = models.FileField(upload_to=media_upload_path)

    class Meta:
        db_table = "message_media"

    def __str__(self):
        return f"{self.content_type} - {self.file.name}"

    def is_image(self):
        return self.content_type.startswith("image/")

    def is_audio(self):
        return self.content_type.startswith("audio/")

    def is_video(self):
        return self.content_type.startswith("video/")

    @property
    def media_type(self):
        if self.content_type.startswith("image/"):
            return "image"
        elif self.content_type.startswith("video/"):
            return "video"
        elif self.content_type.startswith("audio/"):
            return "audio"
        return "other"

class PhoneCall(models.Model):
    phone_call_id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=255, unique=True)
    call_duration = models.IntegerField()
    date_created = models.DateTimeField()
    call_from = models.CharField(max_length=10)
    call_to = models.CharField(max_length=10)
    is_inbound = models.BooleanField(default=False)
    recording_url = models.TextField(null=True)
    status = models.CharField(max_length=50)

    class Meta:
        db_table = "phone_call"

    def save(self, *args, **kwargs):
        self.call_from = self.call_from[-10:]
        self.call_to = self.call_to[-10:]
        super().save(*args, **kwargs)
    
    def get_lead(self):
        from core.models import Lead
        return Lead.objects.filter(phone_number=self.call_from).first() or Lead.objects.filter(phone_number=self.call_to).first()

    def __str__(self):
        return self.external_id

class PhoneCallTranscription(models.Model):
    phone_call_transcription_id = models.AutoField(primary_key=True)
    phone_call = models.ForeignKey(PhoneCall, related_name='transcriptions', on_delete=models.CASCADE, db_column='phone_call_id')
    external_id = models.CharField(max_length=255, unique=True)
    text = models.TextField()
    audio = models.FileField(upload_to='audio/')
    job = models.JSONField(null=True)

    class Meta:
        db_table = "phone_call_transcription"

    def __str__(self):
        return self.external_id