from enum import Enum

class MarketingParams(Enum):
    GoogleURLClickID = 'gclid'
    GoogleAnalyticsCookieClientID = '_ga'

    FacebookURLClickID = 'fbclid'
    FacebookCookieClientID = '_fbp'
    FacebookCookieClickID = '_fbc'

    CallTrackingNumberSessionValue = 'call_tracking_number'

    AdCampaign = 'ad_campaign'
    AdGroup = 'ad_group'