from django.core.management.base import BaseCommand
from core.google.api import google_api_service
from website import settings

class Command(BaseCommand):
    help = "Inspect Google Ads conversion action tag snippets"

    def handle(self, *args, **options):
        conversion_action_id = settings.LEAD_CREATED_GOOGLE_ADS_CONVERSION_ACTION_ID

        gaql = f"""
        SELECT
            offline_conversion_upload_client_summary.client,
            offline_conversion_upload_client_summary.status,
            offline_conversion_upload_client_summary.total_event_count,
            offline_conversion_upload_client_summary.successful_event_count,
            offline_conversion_upload_client_summary.pending_event_count,
            offline_conversion_upload_client_summary.last_upload_date_time
        FROM offline_conversion_upload_client_summary
        """

        rows = google_api_service.query(gaql)

        if not rows:
            self.stdout.write("No conversion action found.")
            return

        for row in rows:
            summary = row.offline_conversion_upload_client_summary
            print(f"Status: {summary.status}")
            print(f"Total: {summary.total_event_count}")
            print(f"Successful: {summary.successful_event_count}")
            print(f"Pending: {summary.pending_event_count}") # Watch this number
            print(f"Last Upload: {summary.last_upload_date_time}")