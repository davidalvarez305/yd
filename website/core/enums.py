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

class LeadEngagementAction(Enum):
    NONE = "none"
    INTIATE_CONTACT = "initiate_contact"
    SEND_FOLLOW_UP = "send_follow_up"
    MARK_NO_RESPONSE = "mark_no_response"

class FollowUpVariant(Enum):
    FIRST = "first"
    SECOND = "second"
