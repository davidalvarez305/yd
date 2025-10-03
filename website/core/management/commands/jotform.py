from django.core.management.base import BaseCommand
from core.esign import esignature_service

class Command(BaseCommand):
    help = "Get active forms in Jotform"

    def handle(self, *args, **options):
        esignature_service.get_forms()