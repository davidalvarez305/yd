from enum import Enum

class InvoiceTypeChoices(Enum):
    DEPOSIT = "DEPOSIT"
    REMAINING = "REMAINING"
    FULL = "FULL"
    EXTEND = 'EXTEND'

    def __str__(self):
        return self.name
    
    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)