from django.contrib import admin
from .models import LeadStatus, LeadInterest, NextAction, ServiceType, UnitType, InvoiceType

admin.site.register(LeadStatus)
admin.site.register(LeadInterest)
admin.site.register(NextAction)
admin.site.register(ServiceType)
admin.site.register(UnitType)
admin.site.register(InvoiceType)
