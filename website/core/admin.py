from django.contrib import admin
from core.models import EventRole, Ingredient, IngredientCategory, LeadStatus, LeadInterest, MarketingCampaign, NextAction, ServiceType, Unit, UnitType, InvoiceType, User

admin.site.register(LeadStatus)
admin.site.register(LeadInterest)
admin.site.register(NextAction)

admin.site.register(UnitType)
admin.site.register(Unit)
admin.site.register(Ingredient)
admin.site.register(IngredientCategory)

admin.site.register(InvoiceType)
admin.site.register(ServiceType)

admin.site.register(User)

admin.site.register(EventRole)

admin.site.register(MarketingCampaign)
