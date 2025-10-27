import requests

from django.core.management.base import BaseCommand, CommandError
from core.facebook.api import facebook_api_service

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            ads = facebook_api_service.get_ad_spend()
            self.stdout.write(self.style.SUCCESS(f'ads: {ads}'))
        except requests.RequestException as e:
            raise CommandError(f'RequestException: {str(e)}')
        except Exception as e:
            raise CommandError(f'Error while fetching follower count: {str(e)}')