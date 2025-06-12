from datetime import timedelta
import requests

from django.utils.timezone import now

from core.facebook.api.base import FacebookAPIServiceInterface
from core.models import FacebookAccessToken

class FacebookAPIService(FacebookAPIServiceInterface):
    def __init__(self, api_version: str, app_id: str, app_secret: str, app_user_token: str):
        self.page_access_token = FacebookAccessToken.objects.order_by('-date_created').first()
        self.api_version = api_version
        self.app_id = app_id
        self.app_secret = app_secret
        self.app_user_token = app_user_token

    def get_lead_data(self, lead):
        leadgen_id = lead.get('leadgen_id')

        if not leadgen_id:
            raise ValueError('leadgen_id cannot be missing from entry.')
        
        if self.page_access_token.refresh_needed:
            self._refresh_access_token()

        url = f'https://graph.facebook.com/{self.api_version}/{leadgen_id}'
        params = {
            'access_token': self.access_token,
            'fields': 'campaign_id,ad_id,form_id,campaign_name,field_data,adset_id,adset_name,created_time,is_organic,ad_name,platform'
        }

        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            raise Exception(f'Failed to retrieve Facebook lead. Status {response.status_code}: {response.text}')

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

    def _refresh_access_token(self):
        """
        Refreshes the Facebook long-lived access token and returns the new token.
        Logs and raises errors if the refresh fails.
        """
        params = {
            'grant_type': 'fb_exchange_token',
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'fb_exchange_token': self.app_user_token,
        }

        try:
            response = requests.get('https://graph.facebook.com/oauth/access_token', params=params)
            response.raise_for_status()
        except requests.RequestException as e:
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