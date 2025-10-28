import requests

from django.core.management.base import BaseCommand, CommandError
from core.facebook.api import facebook_api_service
from core.google.api import google_api_service

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            facebook_ads = facebook_api_service.get_ad_spend()
            self.stdout.write(self.style.SUCCESS(f'facebook_ads: {facebook_ads}'))

            google_ads = google_api_service.get_ad_spend()
            self.stdout.write(self.style.SUCCESS(f'google_ads: {google_ads}'))
        except requests.RequestException as e:
            raise CommandError(f'RequestException: {str(e)}')
        except Exception as e:
            raise CommandError(f'Error while fetching follower count: {str(e)}')