from django.core.management.base import BaseCommand
from core.google.api import google_api_service
from website import settings

class Command(BaseCommand):
    help = "Inspect Google Ads conversion action tag snippets"

    def handle(self, *args, **options):
        conversion_action_id = settings.LEAD_CREATED_GOOGLE_ADS_CONVERSION_ACTION_ID

        gaql = f"""
        SELECT
          conversion_action.id,
          conversion_action.name,
          conversion_action.tag_snippets
        FROM conversion_action
        WHERE conversion_action.id = {conversion_action_id}
        """

        rows = google_api_service.query(gaql)

        if not rows:
            self.stdout.write("No conversion action found.")
            return

        for row in rows:
            action = row.conversion_action

            self.stdout.write(
                "\n".join([
                    f"ID: {action.id}",
                    f"Name: {action.name}",
                    "Tag Snippets:",
                    *(action.tag_snippets or ["(none)"]),
                ])
            )