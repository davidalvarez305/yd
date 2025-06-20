from django.contrib import admin
from core.models import EventRole, IngredientCategory, LeadStatus, LeadInterest, AdCampaign, NextAction, ServiceType, Store, Unit, UnitConversion, UnitType, InvoiceType, User

admin.site.register(LeadStatus)
admin.site.register(LeadInterest)
admin.site.register(NextAction)

admin.site.register(UnitType)
admin.site.register(Unit)
admin.site.register(IngredientCategory)
admin.site.register(Store)
admin.site.register(UnitConversion)

admin.site.register(InvoiceType)
admin.site.register(ServiceType)

admin.site.register(User)

admin.site.register(EventRole)

admin.site.register(AdCampaign)
