import requests

from django.core.management.base import BaseCommand, CommandError
from core.facebook.api import facebook_api_service


class Command(BaseCommand):
    help = 'Get Instagram follower count via Facebook Graph API.'

    def handle(self, *args, **options):
        try:
            followers = facebook_api_service.get_ig_followers()
            self.stdout.write(self.style.SUCCESS(f'Instagram followers: {followers}'))
        except requests.RequestException as e:
            raise CommandError(f'RequestException: {str(e)}')
        except Exception as e:
            raise CommandError(f'Error while fetching follower count: {str(e)}')