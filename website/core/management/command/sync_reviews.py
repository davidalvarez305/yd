from django.core.management.base import BaseCommand
from core.reviews import reviews_service
from core.logger import logger

class Command(BaseCommand):
    help = "Syncs Google Reviews and handles errors gracefully."

    def handle(self, *args, **options):
        self.stdout.write("Starting Google review sync...")
        try:
            reviews_service.sync_reviews()
            self.stdout.write(self.style.SUCCESS("Google reviews synced successfully."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error syncing reviews: {str(e)}"))
            logger.error(str(e))