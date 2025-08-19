from django.core.management.base import BaseCommand, CommandError
from core.models import Event, Lead
from datetime import datetime
from django.db.models import Sum

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            cutoff_date = datetime(2025, 7, 28)
            
            events = Event.objects.filter(lead__created_at__gte=cutoff_date)
            
            total_revenue = events.aggregate(total_amount=Sum('amount'))
            
            total_amount = total_revenue['total_amount'] if total_revenue['total_amount'] is not None else 0
            
            self.stdout.write(f'{events.count()} events found where lead was created after {cutoff_date}')
            self.stdout.write(f'Total amount: ${total_amount:.2f}')
        
        except Exception as e:
            raise CommandError(f'Error retrieving events: {e}')