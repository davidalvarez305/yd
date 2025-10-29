from datetime import timedelta, date
import requests
from django.core.management.base import BaseCommand, CommandError
from core.facebook.api import facebook_api_service
from core.google.api import google_api_service

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            start = date(2025, 10, 1)
            end = date(2025, 10, 27)
            current = start
            while current <= end:
                next_day = current + timedelta(days=1)
                print('START: ', current)
                print('END: ', next_day)
                facebook_api_service.get_ad_spend(
                    start_date=current.isoformat(),
                    end_date=next_day.isoformat(),
                )
                google_api_service.get_ad_spend(
                    start_date=current,
                    end_date=next_day,
                )
                self.stdout.write(self.style.SUCCESS(f"Processed {current}"))
                current = next_day
        except requests.RequestException as e:
            raise CommandError(f"RequestException: {str(e)}")
        except Exception as e:
            raise CommandError(f"Error while fetching ad spend: {str(e)}")