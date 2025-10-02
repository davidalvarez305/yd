import requests

from django.core.management.base import BaseCommand, CommandError
from core.call_tracking import call_tracking_service


class Command(BaseCommand):
    help = 'Get Instagram follower count via Facebook Graph API.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--id',
            type=str,
            required=True,
            help='CallRail Call ID',
        )

    def handle(self, *args, **options):
        call_id = options['id']

        call = call_tracking_service.get_call_by_id(call_id=call_id)

        print(call)
        
