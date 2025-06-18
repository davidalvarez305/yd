from django.http import HttpRequest
from urllib.parse import parse_qs, urlparse
from .enums import ConversionServiceType, MarketingParams
from core.models import Ad, AdCampaign, AdGroup

CLICK_ID_KEYS = ["gclid", "gbraid", "wbraid", "msclkid", "fbclid", "li_fat_id"]

class MarketingHelper:
    def __init__(self, request: HttpRequest):
        self.request = request
        
        self.landing_page = self.request.headers.get('Referer')
        parsed_url = urlparse(self.landing_page)
        self.params = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}

        self.external_id = self.request.session.get('external_id')

        self.referrer = self.request.META.get('HTTP_REFERER')

        self.ip = self.request.META.get('REMOTE_ADDR')
        self.user_agent = self.request.META.get('HTTP_USER_AGENT')

        self.keywords = self.params.get('keyword')
        self.source = self.params.get('source', self.get_source_from_referrer())
        self.medium = self.params.get('medium', self.generate_medium())
        self.channel = self.params.get('channel', self.get_channel())

        marketing_params = self._get_marketing_params()

        self.click_id = marketing_params.get('click_id')
        self.platform_id = marketing_params.get('platform_id')
        self.client_id = marketing_params.get('client_id')

        self.ad = self.get_or_create_ad()
    
    def to_dict(self):
        exclude = {'request', 'ad'}
        data = {
            key: value
            for key, value in self.__dict__.items()
            if key not in exclude
        }

        if self.ad:
            data['ad_id'] = self.ad.ad_id
            data['ad_name'] = self.ad.name
            data['ad_group_id'] = self.ad.adgroup.ad_group_id
            data['ad_group_name'] = self.ad.adgroup.ad_group_name
            data['ad_campaign_id'] = self.ad.adgroup.ad_campaign.ad_campaign_id
            data['ad_campaign_name'] = self.ad.adgroup.ad_campaign.ad_campaign_name

        return data

    def get_cookie(self, cookie_name):
        """
        Returns the value of a cookie if it exists, otherwise None.
        """
        return self.request.COOKIES.get(cookie_name)

    def generate_medium(self):
        """
        Determines the marketing medium based on referrer and query parameters.
        """
        if not self.referrer:
            return "direct"
        elif not self.params:
            return "organic"
        elif self.is_paid():
            return "paid"
        else:
            return "referral"

    def is_paid(self):
        """
        Determines if the traffic is from a paid source (based on query params).
        """
        return any(self.params.get(key) for key in CLICK_ID_KEYS)

    def get_source_from_referrer(self):
        """
        Extracts the source of the traffic from the referrer URL.
        """
        try:
            url = self.referrer if self.referrer else ''
            host = url.split('//')[-1].split('/')[0].lower()
            if host.startswith("www."):
                host = host[4:]
            return host
        except Exception as e:
            print(f"Error parsing referrer: {e}")
            return "unknown"

    def get_channel(self):
        """
        Determines the channel based on the referrer.
        """
        display_networks = ["googleads.g.doubleclick.net"]
        search_engines = [
            "bing", "yahoo", "ecosia", "duckduckgo", "yandex", "baidu", "naver", "ask.com",
            "adsensecustomsearchads", "aol", "brave"
        ]
        major_social_networks = [
            "facebook", "instagram", "twitter", "linkedin", "pinterest", "snapchat", "reddit", "whatsapp",
            "wechat", "telegram", "discord", "vkontakte", "weibo", "line", "kakaotalk", "qq", "viber", "tumblr",
            "flickr", "meetup", "tagged", "badoo", "myspace",
        ]
        major_video_platforms = [
            "youtube", "tiktok", "vimeo", "dailymotion", "twitch", "bilibili", "youku", "rutube", "vine", "peertube",
            "ig tv", "veoh", "metacafe", "vudu", "vidyard", "rumble", "bit chute", "brightcove", "viddler", "vzaar",
        ]

        ref = self.referrer or ""

        for platform in display_networks:
            if platform in ref:
                return "display"
        for engine in search_engines:
            if engine in ref:
                return "search"
        for network in major_social_networks:
            if network in ref:
                return "social"
        for platform in major_video_platforms:
            if platform in ref:
                return "video"

        return "other"

    def get_or_create_ad(self):
        """
        Fetches or creates an ad based on URL parameters.
        """
        ad_id = self.params.get("ad_id")
        ad_name = self.params.get("ad_name")

        ad_group_id = self.params.get("ad_group_id")
        ad_group_name = self.params.get("ad_group_name")

        ad_campaign_id = self.params.get("ad_campaign_id")
        ad_campaign_name = self.params.get("ad_campaign_name")

        if not ad_id or not self.platform_id:
            return None
        
        ad_campaign, _ = AdCampaign.objects.get_or_create(
            ad_campaign_id=ad_campaign_id,
            defaults={
                'name': ad_campaign_name,
            }
        )

        ad_group, _ = AdGroup.objects.get_or_create(
            ad_group_id=ad_group_id,
            defaults={
                'name': ad_group_name,
                'ad_campaign': ad_campaign,
            }
        )

        ad, _ = Ad.objects.get_or_create(
            ad_id=ad_id,
            defaults={
                'platform_id': self.platform_id,
                'name': ad_name,
                'ad_group': ad_group,
            }
        )
        
        return ad

    def _get_marketing_params(self) -> dict:
        """
        Utility function to extract marketing parameters from the URL and cookies.
        Extracts click_id from the URL, client_id from cookies, and platform_id based on the URL parameters.
        """
        # Step 1: Extract `click_id` and `platform_id` from the URL
        click_id = None
        platform_id = None
        client_id = None

        for key in MarketingParams.GoogleURLClickIDKeys.value:
            click_id = self.params.get(key)
            if click_id:
                platform_id = ConversionServiceType.GOOGLE.value
                break

        if not click_id:
            fbclid = self.params.get(MarketingParams.FacebookURLClickID.value, None)
            if fbclid:
                click_id = fbclid
                platform_id = ConversionServiceType.FACEBOOK.value

        # Step 2: Extract `client_id` from cookies based on `platform_id`
        if platform_id == ConversionServiceType.GOOGLE:
            client_id = self.request.COOKIES.get(MarketingParams.GoogleAnalyticsCookieClientID.value, None)
        elif platform_id == ConversionServiceType.FACEBOOK:
            client_id = self.request.COOKIES.get(MarketingParams.FacebookCookieClientID.value, None)

        # Step 3: Return the extracted values
        return {
            "click_id": click_id,
            "client_id": client_id,
            "platform_id": platform_id
        }