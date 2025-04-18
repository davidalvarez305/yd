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

    def get_lead(self):
        from core.models import Lead
        return Lead.objects.filter(phone_number=self.text_from).first() or Lead.objects.filter(phone_number=self.text_to).first()


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
    audio_url = models.TextField()
    text_url = models.TextField()

    class Meta:
        db_table = "phone_call_transcription"

    def __str__(self):
        return self.external_id