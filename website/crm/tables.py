from django.urls import reverse
from core.tables import Table, TableField, TableCellWidget
from core.models import CocktailIngredient, EventCocktail, EventStaff, Ingredient, InternalLog, Message, PhoneCall, Quote, QuotePreset, QuoteService, Service, StoreItem, User, Cocktail, Event, Visit
from core.widgets import DeleteButton, PriceCellWidget
from core.utils import deep_getattr

from django.contrib.auth.models import AbstractUser
from django.utils.timezone import localtime, make_aware, get_current_timezone
from datetime import datetime, time

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
                'value': lambda row: f"{row.start_time.strftime('%B, %d')}: {row.start_time.strftime('%#I %p')} - {row.end_time.strftime('%#I %p')}"
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
            'street_address_two',
            'special_instrucions',
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

class EventCocktailTable(Table):
    delete = TableField(
        name='delete',
        label='Delete',
        cell_widget=DeleteButton(
            context={
                'attrs': {
                    'hx-post': lambda row, request: reverse('eventcocktail_delete', kwargs={ 'pk': row.pk }),
                    'hx-target': '#eventCocktailsTable',
                    'hx-ext': "loading-states",
                    'hx-on--after-request': "modalHelper.get('eventCocktailsModal').close();",
                    'data-loading-target': '#deleteButton',
                    'id': 'deleteButton',
                    'data-loading-class-remove': 'hidden',
                }
            }
        )
    )

    class Meta:
        model = EventCocktail
        exclude=['event_cocktail_id', 'event']
        pk = 'event_cocktail_id'

class EventStaffTable(Table):
    hourly_rate = TableField(
        name='hourly_rate',
        label='Pay Rate',
        cell_widget=TableCellWidget(
            data = {
                'value': lambda row: f"${row.hourly_rate}"
            }
        )
    )
    
    assigned_staff = TableField(
        name='assigned_staff',
        label='Assigned Time',
        cell_widget=TableCellWidget(
            data = {
                'value': lambda row: f"{row.start_time.strftime('%#I %p')} - {row.end_time.strftime('%#I %p')}"
            }
        )
    )

    delete = TableField(
        name='delete',
        label='Delete',
        cell_widget=DeleteButton(
            context={
                'attrs': {
                    'hx-post': lambda row, request: reverse('eventstaff_delete', kwargs={ 'pk': row.pk }),
                    'hx-target': '#eventStaffTable',
                    'hx-ext': "loading-states",
                    'hx-on--after-request': "modalHelper.get('eventStaffModal').close();",
                    'data-loading-target': '#deleteButton',
                    'id': 'deleteButton',
                    'data-loading-class-remove': 'hidden',
                }
            }
        )
    )

    class Meta:
        model = EventStaff
        exclude=['event_staff_id', 'event', 'start_time', 'end_time']
        pk = 'event_staff_id'

class EventStaffTableExternal(Table):
    assigned_staff = TableField(
        name='assigned_staff',
        label='Assigned Time',
        cell_widget=TableCellWidget(
            data = {
                'value': lambda row: f"{row.start_time.strftime('%#I %p')} - {row.end_time.strftime('%#I %p')}"
            }
        )
    )

    class Meta:
        model = EventStaff
        exclude=['event_staff_id', 'event', 'start_time', 'end_time', 'hourly_rate']
        pk = 'event_staff_id'

class CocktailIngredientTable(Table):
    qty = TableField(
        name='qty',
        label='Qty.',
        cell_widget=TableCellWidget(
            data = {
                'value': lambda row: f"{row.amount} {deep_getattr(row, 'unit.abbreviation')}"
            }
        )
    )

    delete = TableField(
        name='delete',
        label='Delete',
        cell_widget=DeleteButton(
            context={
                'attrs': {
                    'hx-post': lambda row, request: reverse('cocktailingredient_delete', kwargs={ 'pk': row.pk }),
                    'hx-target': '#cocktailIngredientsTable',
                    'hx-ext': "loading-states",
                    'hx-on--after-request': "modalHelper.get('cocktailIngredientsModal').close();",
                    'data-loading-target': '#deleteButton',
                    'id': 'deleteButton',
                    'data-loading-class-remove': 'hidden',
                }
            }
        )
    )

    class Meta:
        model = CocktailIngredient
        exclude=['cocktail_ingredient_id', 'cocktail', 'amount', 'unit']
        pk = 'cocktail_ingredient_id'

class IngredientTable(Table):
    ingredient_category = TableField(
        label='Category',
        cell_widget=TableCellWidget(
            data={
                'value': lambda row: deep_getattr(row, 'ingredient_category.name', '')
            }
        )
    )

    store = TableField(
        label='Store',
        cell_widget=TableCellWidget(
            data={
                'value': lambda row: deep_getattr(row, 'store.name', '')
            }
        )
    )

    class Meta:
        model = Ingredient
        exclude=['ingredient_id']
        pk = 'ingredient_id'

class StoreItemTable(Table):
    image = TableField(
        label='Image',
        cell_widget=TableCellWidget(
            data={
                'value': lambda row: (
                    f'<a href="{deep_getattr(row, "image.url", "#")}" target="_blank">View Image</a>'
                    if deep_getattr(row, 'image.url', '') else ''
                ),
                'is_html': True,
            }
        )
    )

    class Meta:
        model = StoreItem
        exclude = ['store_item_id']
        extra_fields = ['view', 'delete']
        pk = 'store_item_id'

class QuoteTable(Table):
    external = TableField(
        label='External',
        cell_widget=TableCellWidget(
            data={
                'value': lambda row: (
                    f'<a href="{reverse("external_quote_view", kwargs={ "external_id": row.external_id })}" target="_blank"'
                    f'class="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-2 py-1 text-sm font-semibold leading-5 text-gray-800 hover:border-gray-300 hover:text-gray-900 hover:shadow-sm focus:ring focus:ring-gray-300/25 active:border-gray-200 active:shadow-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-gray-600 dark:hover:text-gray-200 dark:focus:ring-gray-600/40 dark:active:border-gray-700"'
                    f'>External</a>'
                ),
                'is_html': True,
            }
        )
    )

    event_date = TableField(
        label='Date',
        cell_widget=TableCellWidget(
            data={
                'value': lambda row: localtime(make_aware(datetime.combine(row.event_date, time.min), get_current_timezone())).strftime("%B %d, %Y")
            }
        )
    )

    delete = TableField(
        name='delete',
        label='Delete',
        cell_widget=DeleteButton(
            context = {
                'attrs': {
                    'hx-post': lambda row, request: reverse('quote_delete', kwargs={ 'pk': row.pk }),
                    'hx-target': '#quotesTable',
                    'hx-ext': 'loading-states',
                    'data-loading-target': '#deleteButton',
                    'id': 'deleteButton',
                    'data-loading-class-remove': 'hidden',
                }
            }
        )
    )

    class Meta:
        model = Quote
        exclude = ['quote_id', 'lead', 'external_id', 'services']
        extra_fields = ['view']

class QuoteServiceTable(Table):
    delete = TableField(
        name='delete',
        label='Delete',
        cell_widget=DeleteButton(
            context = {
                'attrs': {
                    'hx-post': lambda row, request: reverse('quoteservice_delete', kwargs={ 'pk': row.pk }),
                    'hx-target': '#quoteServicesTable',
                    'hx-ext': 'loading-states',
                    'data-loading-target': '#deleteButton',
                    'id': 'deleteButton',
                    'data-loading-class-remove': 'hidden',
                }
            }
        )
    )

    class Meta:
        model = QuoteService
        exclude = ['quote_service_id', 'quote']

class QuotePresetTable(Table):
    class Meta:
        model = QuotePreset
        exclude = ['quote_preset_id', 'preset', 'text_content', 'services']
        extra_fields = ['view', 'delete']

class InternalLogTable(Table):
    date_created = TableField(
        label='Date',
        cell_widget=TableCellWidget(
            data={
                'value': lambda row: localtime(row.date_created).strftime("%m/%d/%Y %I:%M %p")
            }
        )
    )

    class Meta:
        model = InternalLog
        extra_fields = ['view']
        exclude = ['logger']