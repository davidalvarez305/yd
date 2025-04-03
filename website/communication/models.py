from django.db import models

class Message(models.Model):
    message_id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=255, unique=True)
    text = models.TextField()
    date_created = models.DateTimeField()
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

class PhoneCall(models.Model):
    phone_call_id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=255, unique=True)
    call_duration = models.IntegerField()
    date_created = models.DateTimeField()
    call_from = models.CharField(max_length=10)
    call_to = models.CharField(max_length=10)
    is_inbound = models.BooleanField(default=False)
    recording_url = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=50)

    class Meta:
        db_table = "phone_call"

    def save(self, *args, **kwargs):
        self.call_from = self.call_from[-10:]
        self.call_to = self.call_to[-10:]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.external_id

class PhoneCallTranscription(models.Model):
    phone_call_transcription_id = models.AutoField(primary_key=True)
    phone_call = models.ForeignKey(PhoneCall, on_delete=models.CASCADE, related_name="transcriptions")
    external_id = models.CharField(max_length=255, unique=True)
    text = models.TextField()
    audio_url = models.URLField()
    text_url = models.URLField()

    class Meta:
        db_table = "phone_call_transcription"

    def __str__(self):
        return self.external_id