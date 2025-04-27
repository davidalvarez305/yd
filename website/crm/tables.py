from core.tables import Table, TableField
from crm.models import Cocktail, Event
from core.models import Service
from core.widgets import DeleteButtonWidget, ViewButtonWidget

# Example Use
""" class CocktailTable(Table):
    class Meta:
        model = Cocktail
        fields = ['name'] """

class CocktailTable(Table):
    view = TableField(name='View', cell_widget=ViewButtonWidget(pk="cocktail_id"))
    name = TableField(name='name', label='Cocktail')
    delete = TableField(name='Delete', cell_widget=DeleteButtonWidget(pk="cocktail_id"))

    class Meta:
        model = Cocktail

class ServiceTable(Table):
    view = TableField(name='View', cell_widget=ViewButtonWidget(pk="service_id"))
    service = TableField(name='service')
    delete = TableField(name='Delete', cell_widget=DeleteButtonWidget(pk="service_id"))

    class Meta:
        model = Service

class EventTable(Table):
    view = TableField(name='View', cell_widget=ViewButtonWidget(pk="event_id"))
    event = TableField(name='name', label='Event')
    delete = TableField(name='Delete', cell_widget=DeleteButtonWidget(pk="event_id"))

    class Meta:
        model = Event