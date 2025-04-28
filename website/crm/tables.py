from core.tables import Table, TableField, TableHeaderWidget
from crm.models import Cocktail, Event
from core.models import Service
from core.widgets import DeleteButton, TemplateCellWidget, ViewButton

class CocktailTable(Table):
    class Meta:
        model = Cocktail
        extra_fields = ['view', 'delete']
        pk = 'cocktail_id'
        detail_url = 'cocktail_detail'
        delete_url = 'cocktail_delete'

class ServiceTable(Table):
    class Meta:
        model = Service
        extra_fields = ['view', 'delete']
        pk = 'service_id'
        detail_url = 'service_detail'
        delete_url = 'service_delete'

class EventTable(Table):
    class Meta:
        model = Event
        extra_fields = ['view', 'delete']
        pk = 'event_id'
        detail_url = 'event_detail'
        delete_url = 'event_delete'