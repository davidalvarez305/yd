from core.tables import Table, TableField, TableHeaderWidget
from crm.models import Cocktail, Event
from core.models import Service
from core.widgets import DeleteButton, TemplateCellWidget, ViewButton

# Example Use
""" 
class CocktailTable(Table):
    class Meta:
        model = Cocktail
        fields = ['name']
        
name = TableField(
    name="name",
    cell_widget=TableCellWidget(data={
        "value": "name",
        "attrs": {
            "hx-get": "/cocktails/{{ row.id }}/edit/",
            "hx-trigger": "click",
            "hx-target": "#modal",
        }
    })
)

cell_widget=TableField(
        name="delete",
        header_widget=TableHeaderWidget("Delete"),
        cell_widget=TemplateCellWidget(
            template="components/delete_button_widget.html",
            context={
                "pk": "{id}",
                "delete_url_name": "cocktail_delete"
            },
            data={"csrf": True}
        )
    ))

ViewButton(url_name="cocktail_detail")
"""

class CocktailTable(Table):
    view = TableField(name='View', cell_widget=ViewButton(pk="cocktail_id", url="cocktail_detail"))
    name = TableField(label='Cocktail')
    delete = TableField(name='Delete', cell_widget=DeleteButton(pk="cocktail_id", url="cocktail_delete"))

    class Meta:
        model = Cocktail

class ServiceTable(Table):
    view = TableField(name='View', cell_widget=ViewButton(pk="service_id", url="service_detail"))
    service = TableField()
    delete = TableField(name='Delete', cell_widget=DeleteButton(pk="service_id", url="service_delete"))

    class Meta:
        model = Service

class EventTable(Table):
    view = TableField(name='View', cell_widget=ViewButton(pk="event_id", url="event_detail"))
    delete = TableField(name='Delete', cell_widget=DeleteButton(pk="event_id", url="event_delete"))

    class Meta:
        model = Event