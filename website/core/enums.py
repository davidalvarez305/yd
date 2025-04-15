from enum import Enum

class AlertStatus(Enum):
    SUCCESS = 'success'
    BAD_REQUEST = 'bad_request'
    INTERNAL_ERROR = 'internal_error'