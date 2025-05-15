from django.http import HttpRequest
from .enums import ConversionServiceType, MarketingParams
from core.models import MarketingCampaign

CLICK_ID_KEYS = ["gclid", "gbraid", "wbraid", "msclkid", "fbclid", "li_fat_id"]

class MarketingHelper:
    def __init__(self, request: HttpRequest):
        self.request = request
        self.landing_page = self.request.build_absolute_uri()

        self.external_id = self.request.session.get('external_id')

        self.referrer = self.request.META.get('HTTP_REFERER')
        self.ip = self.request.META.get('REMOTE_ADDR')
        self.user_agent = self.request.META.get('HTTP_USER_AGENT')

        self.marketing_campaign = self.get_or_create_marketing_campaign()
        self.keywords = self.request.GET.get('keyword')
        self.source = self.request.GET.get('source', self.get_source_from_referrer())
        self.medium = self.request.GET.get('medium', self.generate_medium())
        self.channel = self.request.GET.get('channel', self.get_channel())

        marketing_params = get_marketing_params(request=self.request)

        self.click_id = marketing_params.get('click_id')
        self.platform_id = marketing_params.get('platform_id')
        self.client_id = marketing_params.get('client_id')
    
    def to_dict(self):
        exclude = {'request'}
        return {
            key: value
            for key, value in self.__dict__.items()
            if key not in exclude
        }

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
        elif not self.request.GET:
            return "organic"
        elif self.is_paid(self.request.GET):
            return "paid"
        else:
            return "referral"

    def is_paid(self, query_params):
        """
        Determines if the traffic is from a paid source (based on query params).
        """
        return any(query_params.get(key) for key in CLICK_ID_KEYS)

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

    def get_or_create_marketing_campaign(self):
        """
        Fetches or creates a marketing campaign based on URL parameters.
        """
        ad_campaign_id = self.request.GET.get("ad_campaign")

        if not ad_campaign_id or not self.platform_id:
            return None

        campaign, _ = MarketingCampaign.objects.get_or_create(
            marketing_campaign_id=ad_campaign_id,
            platform_id=self.platform_id,
            defaults={"name": "Unnamed Campaign"}
        )
        return campaign

def get_marketing_params(request: HttpRequest) -> dict:
    """
    Utility function to extract marketing parameters from the URL and cookies.
    Extracts click_id from the URL, client_id from cookies, and platform_id based on the URL parameters.
    """
    # Step 1: Extract `click_id` and `platform_id` from the URL
    click_id = None
    platform_id = None
    client_id = None

    for key in MarketingParams.GoogleURLClickIDKeys.value:
        click_id = request.GET.get(key, None)
        if click_id:
            platform_id = ConversionServiceType.GOOGLE.value
            break

    if not click_id:
        fbclid = request.GET.get(MarketingParams.FacebookURLClickID.value, None)
        if fbclid:
            click_id = fbclid
            platform_id = ConversionServiceType.FACEBOOK.value

    # Step 2: Extract `client_id` from cookies based on `platform_id`
    if platform_id == ConversionServiceType.GOOGLE.value:
        client_id = request.COOKIES.get(MarketingParams.GoogleAnalyticsCookieClientID.value, None)
    elif platform_id == ConversionServiceType.FACEBOOK.value:
        client_id = request.COOKIES.get(MarketingParams.FacebookCookieClientID.value, None)

    # Step 3: Return the extracted values
    return {
        "click_id": click_id,
        "client_id": client_id,
        "platform_id": platform_id
    }