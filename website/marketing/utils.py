import logging
from django.http import HttpRequest

from .enums import ConversionServiceType, MarketingParams
from .models import MarketingCampaign

CLICK_ID_KEYS = ["gclid", "gbraid", "wbraid", "msclkid", "fbclid", "li_fat_id"]

class MarketingHelper:
    def __init__(self, request: HttpRequest):
        self.request = request
        self.landing_page = request.build_absolute_uri()
        self.cookies = request.COOKIES
        self.query_params = request.GET

        # Session variables
        self.external_id = request.session.get('external_id')

        # Header variables
        self.referrer = request.META.get('HTTP_REFERER')
        self.ip = request.META.get('REMOTE_ADDR')

        # Marketing variables
        self.click_id = None
        self.client_id = None
        self.platform_id = None
        self.marketing_campaign = MarketingCampaign.objects.filter(marketing_campaign_id=request.GET.get('ad_campaign')).first()
        self.keywords = request.GET.get('keyword')
        self.source = request.GET.get('source', self.get_source_from_referrer())
        self.medium = request.GET.get('medium', self.generate_medium())
        self.channel = request.GET.get('channel', self.get_channel())

        # Check platform ID based on Google or Facebook click IDs or referrer
        self.set_platform_id()

    def get_client_id(self):
        """
        Determines the client ID based on the URL parameters and cookies.
        Returns the appropriate client ID.
        """
        if any(self.query_params.get(param) for param in MarketingParams.GoogleURLClickIDKeys.value):
            return self.get_cookie(MarketingParams.GoogleAnalyticsCookieClientID.value)
        elif self.query_params.get(MarketingParams.FacebookURLClickID.value):
            return self.get_cookie(MarketingParams.FacebookCookieClientID.value)
        return None

    def get_cookie(self, cookie_name):
        """
        Helper function to retrieve the value of a specific cookie by name.
        """
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
        """
        Checks if the landing page has any paid marketing parameters (like gclid, fbclid, etc.).
        """
        return any(query_params.get(key) for key in CLICK_ID_KEYS)

    def get_click_id(self):
        """
        Retrieve the first valid click ID from the URL parameters.
        """
        for key in CLICK_ID_KEYS:
            if self.query_params.get(key):
                return self.query_params.get(key)
        return None

    def get_source_from_referrer(self):
        """
        Extract the source from the referrer URL (e.g., google.com, facebook.com).
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

    def set_platform_id(self):
        """
        Assign platform_id based on marketing conditions:
        Google (via gclid, gbraid, wbraid) or Facebook (via fbclid, _fbp).
        """
        if any(self.query_params.get(param) for param in MarketingParams.GoogleURLClickIDKeys.value) or 'google.com' in self.referrer:
            self.platform_id = ConversionServiceType.GOOGLE.value
        elif self.query_params.get(MarketingParams.FacebookURLClickID.value) or self.get_cookie(MarketingParams.FacebookCookieClientID.value):
            self.platform_id = ConversionServiceType.FACEBOOK.value

    def get_channel(self):
        """
        Determine the marketing channel based on the referrer.
        Checks if the referrer is part of known categories such as display networks, search engines, social networks, or video platforms.
        Returns the channel type as a string: 'display', 'search', 'social', 'video', or 'other'.
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

        # Check display networks
        for platform in display_networks:
            if platform in self.referrer:
                return "display"

        # Check search engines
        for engine in search_engines:
            if engine in self.referrer:
                return "search"

        # Check social networks
        for network in major_social_networks:
            if network in self.referrer:
                return "social"

        # Check video platforms
        for platform in major_video_platforms:
            if platform in self.referrer:
                return "video"

        return "other"