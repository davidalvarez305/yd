from datetime import date
import requests
from django.core.management.base import BaseCommand, CommandError
from core.facebook.api import facebook_api_service
from core.google.api import google_api_service

class Command(BaseCommand):
    def add_arguments(self, parser):
        # Adding a `--date` argument for the user to specify the date (in YYYY-MM-DD format)
        parser.add_argument(
            '--date',
            type=str,
            help='The date for which to fetch the ad spend (in YYYY-MM-DD format). Defaults to today.',
        )

    def handle(self, *args, **options):
        try:
            arg_date = options.get('date')
            if arg_date:
                query_date = date.fromisoformat(arg_date)
            else:
                query_date = date.today()

            facebook_api_service.get_ad_spend(query_date=query_date.isoformat())
            google_api_service.get_ad_spend(query_date=query_date)
        except requests.RequestException as e:
            raise CommandError(f"RequestException: {str(e)}")
        except Exception as e:
            raise CommandError(f"Error while fetching ad spend: {str(e)}")