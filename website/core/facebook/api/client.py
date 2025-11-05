from datetime import date, time
import json
import requests

from core.facebook.api.base import FacebookAPIServiceInterface
from core.models import Ad, AdSpend, FacebookAccessToken
from core.logger import logger
from website import settings
from core.utils import get_facebook_token_expiry_date, normalize_phone_number
from marketing.utils import create_ad_from_params, parse_datetime
from marketing.enums import ConversionServiceType

class FacebookAPIService(FacebookAPIServiceInterface):
    def __init__(self, api_version: str, app_id: str, app_secret: str, account_id: str):
        self.page_access_token = FacebookAccessToken.objects.order_by('-date_created').first()
        self.api_version = api_version
        self.app_id = app_id
        self.app_secret = app_secret
        self.account_id = account_id

    def get_lead_data(self, lead):
        try:
            leadgen_id = lead.get("leadgen_id")
            if not leadgen_id:
                raise ValueError("leadgen_id cannot be missing from entry.")

            if self.page_access_token.refresh_needed:
                self._refresh_access_token()

            url = f"https://graph.facebook.com/{self.api_version}/{leadgen_id}"
            params = {
                "access_token": self.page_access_token.access_token,
                "fields": "campaign_id,ad_id,form_id,campaign_name,field_data,"
                        "adset_id,adset_name,created_time,is_organic,ad_name,platform"
            }

            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()

            if not data.get("field_data"):
                raise Exception("Incorrectly formatted response: missing field_data.")

            entry = lead.copy()
            entry = self._normalize_field_data(entry, data)

            return entry
        except Exception as e:
            logger.error(e, exc_info=True)
            raise Exception("Error while getting lead data from Facebook.")
    
    def get_ig_followers(self):
        try:
            if self.page_access_token.refresh_needed:
                self._refresh_access_token()

            url = f'https://graph.facebook.com/{self.api_version}/{settings.FACEBOOK_PAGE_ID}'
            params = {
                'access_token': self.page_access_token.access_token,
                'fields': 'instagram_accounts{followers_count}'
            }

            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()

            data = response.json()
            instagram_accounts = data.get('instagram_accounts', {}).get('data', [])
            if not instagram_accounts:
                raise ValueError('No Instagram accounts linked to this page.')

            followers = instagram_accounts[0].get('followers_count')
            if followers is None:
                raise ValueError('followers_count not found in response.')

            return followers

        except Exception as e:
            logger.error(f"Error fetching Instagram followers: {e}", exc_info=True)
            raise Exception('Error while retrieving Instagram follower count.')

    def get_leadgen_forms(self):
        if self.page_access_token.refresh_needed:
            self._refresh_access_token()

        url = f"https://graph.facebook.com/{self.api_version}/{settings.FACEBOOK_PAGE_ID}"
        params = {
            'access_token': self.page_access_token.access_token,
            'fields': 'leadgen_forms{id}',
        }

        response = requests.get(url, params=params, timeout=20)
        if response.status_code != 200:
            raise Exception(f"Error fetching leadgen_forms: {response.json()}")

        data = response.json()
        return data.get('leadgen_forms', {}).get('data', [])

    def get_all_leads_for_form(self, form_id):
        if self.page_access_token.refresh_needed:
            self._refresh_access_token()

        leads = []
        url = f"https://graph.facebook.com/{self.api_version}/{form_id}/leads"
        params = {
            'access_token': self.page_access_token.access_token,
            'fields': 'field_data,ad_id,ad_name,adset_id,adset_name,campaign_id,campaign_name,created_time,form_id,id,partner_name,platform,is_organic',
            'limit': 100,
        }

        while url:
            response = requests.get(url, params=params, timeout=20)
            if response.status_code != 200:
                raise Exception(f"Error fetching leads for form {form_id}: {response.json()}")

            data = response.json()
            leads.extend(data.get('data', []))
            url = data.get('paging', {}).get('next')
            params = {}

        return leads
    
    def _refresh_access_token(self):
        """
        Refreshes the Facebook long-lived access token and returns the new token.
        Logs and raises errors if the refresh fails.
        """
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'fb_exchange_token': self.page_access_token.access_token,
        }

        try:
            response = requests.get('https://graph.facebook.com/oauth/access_token', params=params, timeout=20)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(e, exc_info=True)
            raise Exception('Error during request.')

        data = response.json()

        token = FacebookAccessToken(
            access_token=data.get('access_token'),
            date_expires=get_facebook_token_expiry_date(),
        )
        token.save()

        self.page_access_token = token

    def _normalize_field_name(self, field_name):
        FIELD_MAP = {
            'full_name': ['full_name', 'nombre_completo', 'name'],
            'message': ['message', 'services', 'city', 'brief_description', 'ciudad'],
            'phone_number': ['phone_number', 'telefono'],
            'email': ['email'],
            'city': ['city', 'ciudad'],
            'platform': ['platform'],
            'form_id': ['form_id'],
            'is_organic': ['is_organic'],
            'campaign_id': ['campaign_id'],
            'campaign_name': ['campaign_name'],
            'adset_id': ['adset_id'],
            'adset_name': ['adset_name'],
            'ad_id': ['ad_id'],
            'ad_name': ['ad_name'],
            'created_time': ['created_time'],
        }

        for key, aliases in FIELD_MAP.items():
            for alias in aliases:
                if alias in field_name:
                    return key
    
    def _normalize_field_data(self, lead: dict, data: dict) -> dict:
        fields = data.get("field_data", [])

        for field in fields:
            field_name = self._normalize_field_name(field.get("name"))
            value = field.get("values", [None])[0]

            if field_name and value and not lead.get(field_name):
                if field_name == "phone_number":
                    lead.update({
                        'phone_number': normalize_phone_number(value)
                    })
                else:
                    lead.update({
                        field_name: value
                    })

        for key in [
            "campaign_id",
            "campaign_name",
            "ad_id",
            "ad_name",
            "form_id",
            "adset_id",
            "adset_name",
            "created_time",
            "is_organic",
            "platform",
        ]:
            if key in data:
                if key == 'created_time':
                    lead.update({
                        'created_time': parse_datetime(data[key])
                    })
                else:
                    lead.update({
                        key: data[key]
                    })

        return lead
    
    def get_ad_spend(self, query_date=None):
        if self.page_access_token.refresh_needed:
            self._refresh_access_token()

        try:
            url = f"https://graph.facebook.com/{self.api_version}/act_{self.account_id}/insights"
            params = {
                "access_token": self.page_access_token.access_token,
                "fields": "spend",
            }

            if query_date:
                params["time_range"] = json.dumps({
                    "since": query_date,
                    "until": query_date
                })
            else:
                params["date_preset"] = "last_7d"

            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()

            data = response.json()

            results = data.get('data', [])[0] if data.get('data') else None
            if not results:
                return

            spend = results.get('spend')
            if not spend:
                return
            
            print('spend: ', spend)

            """ AdSpend.objects.create(
                spend=spend,
                date=query_date,
                platform_id=ConversionServiceType.FACEBOOK.value,
            ) """

        except Exception as e:
            print(f'Failed to get ad spend: {e}')

    def get_ads(self):
        try:
            if self.page_access_token.refresh_needed:
                self._refresh_access_token()

            url = f"https://graph.facebook.com/{self.api_version}/act_{self.account_id}/ads"
            params = {
                "access_token": self.page_access_token.access_token,
                "fields": "adset_id,campaign_id,name,id",
                "limit": 100
            }

            all_ads = []
            while url:
                response = requests.get(url, params=params if "after" not in url else None, timeout=20)

                response.raise_for_status()
                data = response.json()

                all_ads.extend(data.get("data", []))
                url = data.get("paging", {}).get("next")

            return all_ads

        except Exception as e:
            logger.error(e, exc_info=True)
            raise Exception("Error while getting ad data from Facebook.")
    
    def create_ad_from_api(self, data: dict):
        params = {
            'ad_id': data.get('ad_id'),
            'ad_name': data.get('ad_name'),
            'ad_group_id': data.get('adset_id'),
            'ad_group_name': data.get('adset_name'),
            'ad_campaign_id': data.get('campaign_id'),
            'ad_campaign_name': data.get('campaign_name'),
        }

        cookies = {
            '_fbc': 1
        }

        return create_ad_from_params(params=params, cookies=cookies)