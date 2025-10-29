import base64
from email.mime.text import MIMEText
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from googleapiclient.discovery import build

from google.ads.googleads.client import GoogleAdsClient

from core.models import Ad, AdSpend, GoogleAccessToken
from core.logger import logger
from core.utils import load_google_credentials
from marketing.utils import create_ad_from_params

class GoogleAPIService:
    def __init__(self):
        self.token = GoogleAccessToken.objects.order_by("-date_created").first()
        if not self.token:
            raise Exception("No Google access token found in DB.")

        self.creds = load_google_credentials()
        self.gmail = self.build("gmail", "v1")
        self.sheets = self.build("sheets", "v4")
        self.google_ads_client = self.build_ads_client()

    def build(self, api_name: str, api_version: str):
        return build(api_name, api_version, credentials=self.creds)
    
    def build_ads_client(self):
        return GoogleAdsClient.load_from_dict({
            "developer_token": settings.GOOGLE_ADS_DEVELOPER_TOKEN,
            "client_id": self.creds.client_id,
            "client_secret": self.creds.client_secret,
            "refresh_token": self.creds.refresh_token,
            "login_customer_id": settings.GOOGLE_ADS_CUSTOMER_ID,
            "use_proto_plus": True,
        })

    def send_email(self, to: str, subject: str, body: str) -> None:
        try:
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            self.gmail.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()
        except Exception as e:
            logger.error("Failed to send email via Gmail API", exc_info=True)
            raise
    
    def send_html_email(self, to: str, subject: str, html: str) -> None:
        try:
            message = MIMEText(html, "html")
            message["to"] = to
            message["subject"] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            self.gmail.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()
        except Exception as e:
            logger.error("Failed to send email via Gmail API", exc_info=True)
            raise

    def get_sheet_data(self, spreadsheet_id: str, range: str) -> list[dict]:
        try:
            sheet = self.sheets.spreadsheets().values()
            result = sheet.get(spreadsheetId=spreadsheet_id, range=range).execute()
            values = result.get("values", [])
            headers = values[0] if values else []
            return [dict(zip(headers, row)) for row in values[1:]]
        except Exception as e:
            logger.error("Failed to fetch Google Sheet data", exc_info=True)
            raise

    def append_sheet_data(self, spreadsheet_id: str, range: str, data: list[dict]) -> dict:
        try:
            if not data:
                return {}

            headers = list(data[0].keys())
            rows = [[str(row.get(h, "")) for h in headers] for row in data]
            body = {"values": [headers] + rows}

            return self.sheets.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range,
                valueInputOption="RAW",
                body=body
            ).execute()
        except Exception as e:
            logger.error("Failed to append to Google Sheet", exc_info=True)
            raise

    def get_ad_spend(self, start_date=None, end_date=None):
        try:
            if not start_date:
                start_date = timezone.now() - timedelta(days=7)
                start_date = start_date.date()
            if not end_date:
                end_date = timezone.now().date()

            service = self.google_ads_client.get_service("GoogleAdsService")

            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    ad_group.id,
                    ad_group.name,
                    ad_group_criterion.keyword.text,
                    segments.date,
                    metrics.cost_micros
                FROM keyword_view
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
                ORDER BY segments.date ASC
            """

            ad_query = """
                SELECT
                    ad_group.id,
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.name
                FROM ad_group_ad
            """

            ad_stream = service.search_stream(
                customer_id=self.google_ads_client.login_customer_id,
                query=ad_query,
            )

            ad_map = {}
            for batch in ad_stream:
                for row in batch.results:
                    ad_map[row.ad_group.id] = {
                        "ad_id": row.ad_group_ad.ad.id,
                        "ad_name": row.ad_group_ad.ad.name,
                    }

            stream = service.search_stream(
                customer_id=self.google_ads_client.login_customer_id,
                query=query,
            )

            data = []
            for batch in stream:
                for row in batch.results:
                    ad_info = ad_map.get(row.ad_group.id, {})
                    data.append({
                        'ad_campaign_name': row.campaign.name,
                        'ad_campaign_id': row.campaign.id,
                        'ad_group_name': row.ad_group.name,
                        'ad_group_id': row.ad_group.id,
                        'keyword': row.ad_group_criterion.keyword.text,
                        'spend': row.metrics.cost_micros / 1_000_000,
                        'date': row.segments.date,
                        'ad_id': ad_info.get('ad_id'),
                        'ad_name': ad_info.get('ad_name'),
                    })
            
            for row in data:

                ad = Ad.objects.filter(name=row.get('keyword')).first()
                if not ad:
                    ad = create_ad_from_params(params=row, cookies={ 'gclid': 1 })
                
                AdSpend.objects.create(
                    spend=row.get('spend'),
                    date=start_date,
                    ad=ad,
                )

        except Exception as e:
            logger.exception(f"Error fetching Google Ads spend data: {e}", exc_info=True)
            return []