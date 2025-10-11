from django.contrib import admin
from core.models import *

admin.site.register(LandingPageConversion)

admin.site.register(Lead)
admin.site.register(LeadStatus)

admin.site.register(UnitType)
admin.site.register(Unit)
admin.site.register(IngredientCategory)
admin.site.register(Store)
admin.site.register(UnitConversion)

admin.site.register(InvoiceType)
admin.site.register(ServiceType)

admin.site.register(User)

admin.site.register(EventRole)

admin.site.register(FacebookAccessToken)

admin.site.register(GoogleReview)
admin.site.register(GoogleAccessToken)