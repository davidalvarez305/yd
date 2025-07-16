from datetime import timedelta
import requests

from django.utils.timezone import now

from core.facebook.api.base import FacebookAPIServiceInterface
from core.models import FacebookAccessToken
from core.logger import logger
from website import settings

class FacebookAPIService(FacebookAPIServiceInterface):
    def __init__(self, api_version: str, app_id: str, app_secret: str):
        self.page_access_token = FacebookAccessToken.objects.order_by('-date_created').first()
        self.api_version = api_version
        self.app_id = app_id
        self.app_secret = app_secret

    def get_lead_data(self, lead):
        try:
            leadgen_id = lead.get('leadgen_id')

            if not leadgen_id:
                raise ValueError('leadgen_id cannot be missing from entry.')
            
            if self.page_access_token.refresh_needed:
                self._refresh_access_token()

            url = f'https://graph.facebook.com/{self.api_version}/{leadgen_id}'
            params = {
                'access_token': self.page_access_token.access_token,
                'fields': 'campaign_id,ad_id,form_id,campaign_name,field_data,adset_id,adset_name,created_time,is_organic,ad_name,platform'
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            if response.status_code != 200:
                logger.error(e, exc_info=True)
                raise Exception(f'Failed to retrieve Facebook lead.')

            data = response.json()
            fields = data.get('field_data')
            
            if not fields:
                raise Exception('Incorrectly formatted response: missing field_data.')

            entry = lead.copy()

            for field in fields:
                name = field.get('name')
                value = field.get('values', [None])[0]
                if name and value and not entry.get(name):
                    entry[name] = value

            for key in ['campaign_id', 'campaign_name', 'ad_id', 'ad_name', 'form_id', 'adset_id', 'adset_name', 'created_time', 'is_organic', 'platform']:
                if key in data:
                    entry[key] = data[key]

            return entry
        except Exception as e:
            logger.error(e, exc_info=True)
            raise Exception('Error while getting lead data from Facebook.')
    
    def get_ig_followers(self):
        try:
            if self.page_access_token.refresh_needed:
                self._refresh_access_token()

            url = f'https://graph.facebook.com/{self.api_version}/{settings.FACEBOOK_PAGE_ID}'
            params = {
                'access_token': self.page_access_token.access_token,
                'fields': 'instagram_accounts{followers_count}'
            }

            response = requests.get(url, params=params)
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

        response = requests.get(url, params=params)
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
            response = requests.get(url, params=params)
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
            response = requests.get('https://graph.facebook.com/oauth/access_token', params=params)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(e, exc_info=True)
            raise Exception('Error during request.')

        data = response.json()
        expires_in = data.get('expires_in')

        if not data.get('access_token') or not isinstance(expires_in, int):
            raise ValueError('Invalid response.')
        
        token = FacebookAccessToken(
            access_token=data.get('access_token'),
            date_expires=now() + timedelta(seconds=expires_in),
        )
        token.save()

        self.page_access_token = token