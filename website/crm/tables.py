from core.tables import Table, TableField
from crm.models import Cocktail
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