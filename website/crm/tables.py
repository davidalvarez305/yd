from core.tables import Table, TableField, TableCellWidget
from core.models import Service, User, Cocktail, Event
from core.widgets import PriceCellWidget
from django.contrib.auth.models import AbstractUser

class CocktailTable(Table):
    class Meta:
        model = Cocktail
        extra_fields = ['view', 'delete']
        exclude = ['cocktail_id']
        pk = 'cocktail_id'
        detail_url = 'cocktail_detail'
        delete_url = 'cocktail_delete'

class ServiceTable(Table):
    suggested_price = TableField(cell_widget=PriceCellWidget(data={"value": "suggested_price"}), label='Price')
    
    class Meta:
        model = Service
        extra_fields = ['view', 'delete']
        exclude = ['service_id']
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

class UserTable(Table):
    full_name = TableField(
        label='Full Name',
        cell_widget=TableCellWidget(
            data={'value': lambda row: f"{row.first_name} {row.last_name}"}
        )
    )
    
    class Meta:
        model = User
        extra_fields = ['view', 'delete']
        user_fields = ['user_id', 'password', 'forward_phone_number', 'events']
        exclude = [field.name for field in AbstractUser._meta.get_fields()]
        exclude += user_fields
        pk = 'user_id'
        detail_url = 'user_detail'
        delete_url = 'user_delete'