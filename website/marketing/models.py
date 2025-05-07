from django.db import models
from core.models import LeadMarketing

class Visit(models.Model):
    visit_id = models.AutoField(primary_key=True)
    external_id = models.CharField(max_length=255, db_index=True)
    referrer = models.URLField(null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    url = models.URLField()
    session_duration = models.FloatField(default=0.0)
    
    lead_marketing = models.ForeignKey(LeadMarketing,
        null=True, on_delete=models.SET_NULL,
        related_name='visits'
    )

    def __str__(self):
        return f"Visit {self.visit_id} - {self.url} from {self.referrer}"

    class Meta:
        db_table = 'visit'