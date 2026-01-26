from django.contrib import admin
from core.models import *

admin.site.register(LeadStatus)

# Cocktail Ingredients
admin.site.register(UnitType)
admin.site.register(Unit)
admin.site.register(IngredientCategory)
admin.site.register(Store)
admin.site.register(UnitConversion)

# Quotes & Invoices
admin.site.register(InvoiceType)
admin.site.register(ServiceType)

admin.site.register(User)

admin.site.register(EventRole)

admin.site.register(GoogleReview)

# Choice tables
admin.site.register(BusinessSegment)
admin.site.register(DriverStopStatus)
admin.site.register(ItemState)
admin.site.register(OrderStatus)
admin.site.register(OrderTask)
admin.site.register(OrderTaskStatus)
admin.site.register(UserRole)

# Inventory / Items
admin.site.register(ItemCategory)
admin.site.register(Item)
admin.site.register(ItemStateChangeHistory)

# Orders
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(OrderService)

# Addressing / Geography
admin.site.register(State)
admin.site.register(City)
admin.site.register(ZipCode)
admin.site.register(Address)
admin.site.register(RouteZone)
admin.site.register(OrderAddress)

# Driver / Routing
admin.site.register(DriverRoute)
admin.site.register(DriverStop)
admin.site.register(DriverStopImage)

# Service relationships
admin.site.register(ServiceBusinessSegment)