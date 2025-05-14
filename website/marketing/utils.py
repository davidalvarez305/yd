from django.http import HttpRequest

from .enums import ConversionServiceType, MarketingParams
from core.models import MarketingCampaign

CLICK_ID_KEYS = ["gclid", "gbraid", "wbraid", "msclkid", "fbclid", "li_fat_id"]

class MarketingHelper:
    def __init__(self, request: HttpRequest):
        self.request = request
        self.landing_page = self.request.build_absolute_uri()
        self.cookies = self.request.COOKIES
        self.query_params = self.request.GET

        self.external_id = self.request.session.get('external_id')

        self.referrer = self.request.META.get('HTTP_REFERER')
        self.ip = self.request.META.get('REMOTE_ADDR')
        self.user_agent = self.request.META.get('HTTP_USER_AGENT')

        self.click_id = None
        self.client_id = None
        self.platform_id = None
        self.marketing_campaign = None
        self.keywords = None
        self.source = None
        self.medium = None
        self.channel = None

        self.build()

    def build(self):
        """
        Executes the correct order of operations to populate dependent fields.
        """
        self.set_platform_id()
        self.marketing_campaign = self.get_or_create_marketing_campaign()
        self.keywords = self.query_params.get('keyword')
        self.source = self.query_params.get('source', self.get_source_from_referrer())
        self.medium = self.query_params.get('medium', self.generate_medium())
        self.channel = self.query_params.get('channel', self.get_channel())

    def get_client_id(self):
        if any(self.query_params.get(param) for param in MarketingParams.GoogleURLClickIDKeys.value):
            return self.get_cookie(MarketingParams.GoogleAnalyticsCookieClientID.value)
        elif self.query_params.get(MarketingParams.FacebookURLClickID.value):
            return self.get_cookie(MarketingParams.FacebookCookieClientID.value)
        return None

    def get_cookie(self, cookie_name):
        return self.cookies.get(cookie_name)

    def generate_medium(self):
        if not self.referrer:
            return "direct"
        elif not self.query_params:
            return "organic"
        elif self.is_paid(self.query_params):
            return "paid"
        else:
            return "referral"

    def is_paid(self, query_params):
        return any(query_params.get(key) for key in CLICK_ID_KEYS)

    def get_click_id(self):
        for key in CLICK_ID_KEYS:
            if self.query_params.get(key):
                return self.query_params.get(key)
        return None

    def get_source_from_referrer(self):
        try:
            url = self.referrer if self.referrer else ''
            host = url.split('//')[-1].split('/')[0].lower()
            if host.startswith("www."):
                host = host[4:]
            return host
        except Exception as e:
            print(f"Error parsing referrer: {e}")
            return "unknown"

    def set_platform_id(self):
        if any(self.query_params.get(param) for param in MarketingParams.GoogleURLClickIDKeys.value) or 'google.com' in (self.referrer or ''):
            self.platform_id = ConversionServiceType.GOOGLE.value
        elif self.query_params.get(MarketingParams.FacebookURLClickID.value) or self.get_cookie(MarketingParams.FacebookCookieClientID.value):
            self.platform_id = ConversionServiceType.FACEBOOK.value

    def get_channel(self):
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

    def get_or_create_marketing_campaign(self):
        ad_campaign_id = self.query_params.get("ad_campaign")

        if not ad_campaign_id or not self.platform_id:
            return None

        campaign, _ = MarketingCampaign.objects.get_or_create(
            marketing_campaign_id=ad_campaign_id,
            platform_id=self.platform_id,
            defaults={"name": "Unnamed Campaign"}
        )
        return campaign