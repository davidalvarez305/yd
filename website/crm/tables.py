from core.tables import Table, TableField, TableCellWidget
from core.models import CallTrackingNumber, Message, PhoneCall, Service, User, Cocktail, Event, Visit
from core.widgets import PriceCellWidget
from core.utils import deep_getattr

from django.contrib.auth.models import AbstractUser
from django.utils.timezone import localtime

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
    event_time = TableField(
        name='event_time',
        label='Event Time',
        cell_widget=TableCellWidget(
            data = {
                'value': lambda row: f"{row.start_time.strftime('%Y-%m-%d')} {row.start_time.strftime('%#I %p')} - {row.end_time.strftime('%#I %p')}"
            }
        )
    )

    address = TableField(
        name='address',
        label='Address',
        cell_widget=TableCellWidget(
            data = {
                'value': lambda row: f"{row.street_address}, {row.city}, {row.zip_code}"
            }
        )
    )

    class Meta:
        model = Event
        extra_fields = ['view', 'delete']
        exclude = [
            'event_id',
            'date_created',
            'date_paid',
            'tip',
            'cocktail',
            'start_time',
            'end_time',
            'street_address',
            'city',
            'zip_code',
            'amount',
        ]
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

class PhoneCallTable(Table):
    date_created = TableField(
        label='Date',
        cell_widget=TableCellWidget(
            data={
                'value': lambda row: localtime(row.date_created).strftime("%m/%d/%Y %I:%M %p")
            }
        )
    )

    class Meta:
        model = PhoneCall
        extra_fields = ['view']
        pk = 'phone_call_id'
        detail_url = 'phonecall_detail'
        exclude = ['external_id', 'phone_call_id', 'recording_url']

class MessageTable(Table):
    date_created = TableField(
        label='Date',
        cell_widget=TableCellWidget(
            data={
                'value': lambda row: localtime(row.date_created).strftime("%m/%d/%Y %I:%M %p")
            }
        )
    )

    class Meta:
        model = Message
        extra_fields = ['view']
        pk = 'message_id'
        detail_url = 'message_detail'
        exclude = ['external_id', 'message_id']

class VisitTable(Table):
    date_created = TableField(
        label='Date',
        cell_widget=TableCellWidget(
            data={
                'value': lambda row: localtime(row.date_created).strftime("%m/%d/%Y %I:%M %p")
            }
        )
    )

    lead = TableField(
        label='Lead',
        cell_widget=TableCellWidget(
            data={
                'value': lambda row: deep_getattr(row, 'lead_marketing.lead', '')
            }
        )
    )

    lead_marketing = TableField(
        label='Marketing',
        cell_widget=TableCellWidget(
            data={
                'value': lambda row: deep_getattr(row, 'lead_marketing.marketing_campaign.name', '')
            }
        )
    )

    class Meta:
        model = Visit
        exclude = ['visit_id', 'external_id', 'referrer', 'url']