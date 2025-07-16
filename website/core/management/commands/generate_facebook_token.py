from datetime import timedelta
import requests

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.conf import settings

from core.models import FacebookAccessToken


class Command(BaseCommand):
    help = 'Refresh Facebook long-lived access token and save it to the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--print',
            action='store_true',
            help='Print the new access token after saving it.'
        )

    def handle(self, *args, **options):
        latest_token = FacebookAccessToken.objects.order_by('-date_created').first()

        if not latest_token:
            raise CommandError('No existing Facebook access token found in the database.')

        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': settings.FACEBOOK_APP_ID,
            'client_secret': settings.FACEBOOK_APP_SECRET,
            'fb_exchange_token': latest_token.access_token,
        }

        self.stdout.write('🔄 Requesting new long-lived access token...')

        try:
            response = requests.get('https://graph.facebook.com/oauth/access_token', params=params)
            response.raise_for_status()
        except requests.RequestException as e:
            raise CommandError(f'Error while refreshing access token: {str(e)}')

        data = response.json()
        new_token = data.get('access_token')
        expires_in = data.get('expires_in')

        print('data: ', data)

        if not new_token or not isinstance(expires_in, int):
            raise CommandError('Invalid response from Facebook API.')

        token = FacebookAccessToken(
            access_token=new_token,
            date_expires=timezone.now() + timedelta(seconds=expires_in)
        )

        token.save()

        self.stdout.write(self.style.SUCCESS('✅ New access token saved to the database.'))

        if options['print']:
            self.stdout.write(f'\n🔐 New Token: {new_token}\n🕓 Expires in: {expires_in} seconds')