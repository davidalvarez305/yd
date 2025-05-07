from django.contrib import admin
from .models import EventRole, LeadStatus, LeadInterest, NextAction, ServiceType, UnitType, InvoiceType, User, Lead

admin.site.register(LeadStatus)
admin.site.register(LeadInterest)
admin.site.register(NextAction)
admin.site.register(ServiceType)
admin.site.register(UnitType)
admin.site.register(InvoiceType)
admin.site.register(User)

admin.site.register(EventRole)
