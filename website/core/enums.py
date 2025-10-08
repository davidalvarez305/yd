from enum import Enum

class AlertStatus(Enum):
    SUCCESS = 'success'
    BAD_REQUEST = 'bad_request'
    INTERNAL_ERROR = 'internal_error'

class AlertHTTPCodes(Enum):
    SUCCESS = 200
    BAD_REQUEST = 400
    INTERNAL_ERROR = 500

    @classmethod
    def get_http_code(cls, alert_status):
        return cls[alert_status.name].value

class LeadActivityEnum(Enum):
    WEBSITE_VISIT = 'website_visit'
    TEXT_SENT = 'text_sent'

    def __str__(self):
        return self.value
    
    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)

class LeadTaskEnum(Enum):
    GOOGLE = 1
    FACEBOOK = 2

    def __str__(self):
        return self.value
    
    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)