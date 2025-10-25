from django.core.management.base import BaseCommand, CommandError
from core.google.api import google_api_service

class Command(BaseCommand):
    help = "Fetch data from a specific Google Sheet and print it."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sheet_id",
            type=str,
            required=True,
            help="The ID of the Google Spreadsheet.",
        )
        parser.add_argument(
            "--range",
            type=str,
            required=True,
            help="The range to fetch (e.g., 'Sheet1!A1:D10').",
        )

    def handle(self, *args, **options):
        sheet_id = options.get("sheet_id")
        range_name = options.get("range")

        if not sheet_id or not range_name:
            raise CommandError("--sheet_id and --range are required.")

        try:
            data = google_api_service.get_sheet_data(
                spreadsheet_id=sheet_id,
                range=range_name,
            )
            self.stdout.write(self.style.SUCCESS(f"Fetched {len(data)} rows."))
            for row in data:
                self.stdout.write(str(row))
        except Exception as e:
            raise CommandError(f"Failed to fetch sheet data: {e}")