from django.db.models import OuterRef, Subquery, DateTimeField, Q
from django.db.models.functions import Greatest
from django.utils.timezone import now, timedelta
from django.core.management.base import BaseCommand, CommandError

from core.models import Lead, LeadStatusEnum, Message, PhoneCall

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            last_msg_subq = Message.objects.filter(
                Q(text_from=OuterRef("phone_number")) | Q(text_to=OuterRef("phone_number"))
            ).order_by("-date_created").values("date_created")[:1]

            last_call_subq = PhoneCall.objects.filter(
                Q(call_from=OuterRef("phone_number")) | Q(call_to=OuterRef("phone_number"))
            ).order_by("-date_created").values("date_created")[:1]

            # Annotate leads with last contact datetime
            leads = Lead.objects.annotate(
                last_msg_date=Subquery(last_msg_subq, output_field=DateTimeField()),
                last_call_date=Subquery(last_call_subq, output_field=DateTimeField()),
            ).annotate(
                last_contact=Greatest("last_msg_date", "last_call_date")
            )

            # Filter leads where last_contact > 7 days ago
            cutoff = now() - timedelta(days=7)
            leads = leads.filter(last_contact__lt=cutoff)

            for lead in leads:
                has_event = lead.events.count() > 0
                is_archived = lead.lead_status.status == LeadStatusEnum.ARCHIVED
                
                if has_event and is_archived:
                    continue
                
                self.stdout.write(f"{lead} - Last contact: {lead.last_contact}")

        except Exception as e:
            raise CommandError(f"Error retrieving leads: {e}")