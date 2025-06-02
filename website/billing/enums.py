from enum import Enum

class InvoiceTypeChoices(Enum):
    DEPOSIT = "Deposit"
    REMAINING = "Remaining"
    FULL = "Full"
    SERVICE_EXTENSION = 'Service Extension'