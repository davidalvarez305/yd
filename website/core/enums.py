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