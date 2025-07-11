from django.contrib import admin
from core.models import CallTracking, CallTrackingNumber, EventRole, FacebookAccessToken, IngredientCategory, Invoice, Lead, LeadStatus, LeadInterest, AdCampaign, LeadStatusHistory, Message, NextAction, PhoneCall, PhoneCallStatusHistory, ServiceType, Store, Unit, UnitConversion, UnitType, InvoiceType, User, GoogleReview

admin.site.register(CallTracking)
admin.site.register(CallTrackingNumber)

admin.site.register(Lead)
admin.site.register(LeadStatus)
admin.site.register(LeadInterest)
admin.site.register(NextAction)
admin.site.register(LeadStatusHistory)

admin.site.register(UnitType)
admin.site.register(Unit)
admin.site.register(IngredientCategory)
admin.site.register(Store)
admin.site.register(UnitConversion)

admin.site.register(Invoice)
admin.site.register(InvoiceType)
admin.site.register(ServiceType)

admin.site.register(User)

admin.site.register(EventRole)

admin.site.register(AdCampaign)
admin.site.register(FacebookAccessToken)

admin.site.register(GoogleReview)

admin.site.register(Message)
admin.site.register(PhoneCall)
admin.site.register(PhoneCallStatusHistory)