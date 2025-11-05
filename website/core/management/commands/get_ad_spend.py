from datetime import date, timedelta
import requests
from django.core.management.base import BaseCommand, CommandError
from core.facebook.api import facebook_api_service
from core.google.api import google_api_service

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='The date for which to fetch the ad spend (in YYYY-MM-DD format). Defaults to today.',
        )
        
        parser.add_argument(
            '--from_date',
            type=str,
            help='The start date for the range (in YYYY-MM-DD format).',
        )
        
        parser.add_argument(
            '--to_date',
            type=str,
            help='The end date for the range (in YYYY-MM-DD format).',
        )

    def handle(self, *args, **options):
        try:
            from_date_str = options.get('from_date')
            to_date_str = options.get('to_date')
            
            if from_date_str and to_date_str:
                from_date = date.fromisoformat(from_date_str)
                to_date = date.fromisoformat(to_date_str)
                
                current_date = from_date
                while current_date <= to_date:
                    facebook_api_service.get_ad_spend(query_date=current_date.isoformat())
                    google_api_service.get_ad_spend(query_date=current_date)
                    
                    current_date += timedelta(days=1)
            
            elif options.get('date'):
                query_date = date.fromisoformat(options['date'])
                facebook_api_service.get_ad_spend(query_date=query_date.isoformat())
                google_api_service.get_ad_spend(query_date=query_date)
            
            else:
                query_date = date.today()
                facebook_api_service.get_ad_spend(query_date=query_date.isoformat())
                google_api_service.get_ad_spend(query_date=query_date)

        except requests.RequestException as e:
            raise CommandError(f"RequestException: {str(e)}")
        except Exception as e:
            raise CommandError(f"Error while fetching ad spend: {str(e)}")