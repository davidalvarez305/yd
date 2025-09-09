from enum import Enum

class MarketingParams(Enum):
    GoogleURLClickIDKeys = 'gclid', 'gbraid', 'wbraid'
    GoogleAnalyticsCookieClientID = '_ga'

    FacebookURLClickID = 'fbclid'
    FacebookCookieClientID = '_fbp'
    FacebookCookieClickID = '_fbc'

    def __str__(self):
        return self.value
    
    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)

class ConversionServiceType(Enum):
    GOOGLE = 1
    FACEBOOK = 2

    def __str__(self):
        return self.value
    
    def __eq__(self, other):
        if isinstance(other, int):
            return self.value == other
        return super().__eq__(other)