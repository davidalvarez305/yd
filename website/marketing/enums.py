from enum import Enum

class MarketingParams(Enum):
    GoogleURLClickIDKeys = ['gclid', 'gbraid', 'wbraid']
    GoogleAnalyticsCookieClientID = '_ga'

    FacebookURLClickID = 'fbclid'
    FacebookCookieClientID = '_fbp'
    FacebookCookieClickID = '_fbc'

    CallTrackingNumberSessionValue = 'call_tracking_number'

    AdCampaign = 'ad_campaign'
    AdGroup = 'ad_group'

class ConversionServiceType(Enum):
    GOOGLE = 1
    FACEBOOK = 2