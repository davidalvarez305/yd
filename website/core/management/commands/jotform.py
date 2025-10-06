from django.core.management.base import BaseCommand
from core.esign import esignature_service

# python sdk https://www.jotform.com/developers/libraries/#jotform-api-python
# rest api https://api.jotform.com/docs/#overview

class Command(BaseCommand):
    help = "Get active forms in Jotform"

    def handle(self, *args, **options):
        esignature_service.get_forms()