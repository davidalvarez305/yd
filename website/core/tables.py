from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .widgets import DeleteButton, TableCellWidget, TableHeaderWidget, ViewButton

# Example Use
""" 
class CocktailTable(Table):
    class Meta:
        model = Cocktail
        fields = ['name']

CocktailTable = Table.from_model(Cocktail, exclude=["created_at", "updated_at"])

full_name = TableField(
    label='Full Name',
    cell_widget=TableCellWidget(
        data={'value': lambda row: f"{row.first_name} {row.last_name}"}
    )
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

ViewButton(pk="cocktail_id", url="cocktail_detail")
"""

class TableField:
    def __init__(self, name=None, label=None, header_widget=None, cell_widget=None):
        self.name = name
        self._label = label
        self._header_widget = header_widget
        self._cell_widget = cell_widget

    @property
    def label(self):
        if self._label:
            return self._label
        if self.name:
            return self.name.replace("_", " ").title()
        return ""

    @property
    def header_widget(self):
        if self._header_widget:
            return self._header_widget
        return TableHeaderWidget(self.label)

    @property
    def cell_widget(self):
        if self._cell_widget:
            return self._cell_widget
        return self.build_default_cell_widget()

    def build_default_cell_widget(self):
        return TableCellWidget(data={"value": self.name})
    
    @classmethod
    def from_model_field(cls, field_obj):
        """
        Creates a TableField from a Django model field automatically.
        """
        name = field_obj.name
        label = getattr(field_obj, "verbose_name", name).title()
        return cls(name=name, label=label)

class DeclarativeTableMeta(type):
    def __new__(cls, name, bases, attrs):
        declared_fields = {
            key: value for key, value in attrs.items()
            if isinstance(value, TableField)
        }

        new_class = super().__new__(cls, name, bases, attrs)

        meta = attrs.get('Meta', None)
        if not meta:
            new_class._declared_fields = declared_fields
            return new_class

        model = getattr(meta, 'model', None)
        include_fields = getattr(meta, 'fields', None)
        exclude_fields = getattr(meta, 'exclude', [])
        extra_fields = getattr(meta, 'extra_fields', [])

        prefix = f"{model.__name__.lower()}_"
        pk = getattr(meta, 'pk', prefix + "id")
        detail_url = getattr(meta, 'detail_url', prefix + "detail")
        delete_url = getattr(meta, 'delete_url', prefix + "delete")

        _declared_fields = {}

        if "view" in extra_fields:
            _declared_fields["view"] = TableField(
                name="View",
                cell_widget=ViewButton(pk=pk, url=detail_url)
            )

        if model:
            if include_fields:
                field_names = include_fields
            else:
                field_names = [f.name for f in model._meta.get_fields() if f.concrete and not f.auto_created]

            for field_name in field_names:
                if field_name in exclude_fields:
                    continue
                if field_name not in declared_fields:
                    _declared_fields[field_name] = TableField(name=field_name)
                else:
                    _declared_fields[field_name] = declared_fields[field_name]

        for key, field in declared_fields.items():
            if include_fields and key not in include_fields:
                continue
            if key not in _declared_fields:
                _declared_fields[key] = field

        if "delete" in extra_fields:
            _declared_fields["delete"] = TableField(
                name="Delete",
                cell_widget=DeleteButton(view_name=delete_url)
            )

        new_class._declared_fields = _declared_fields
        return new_class

class Table(metaclass=DeclarativeTableMeta):
    def __init__(self, data=None, request=None):
        self.data = data or []
        self.request = request

    def get_fields(self):
        return list(self._declared_fields.values())

    def render_header(self):
        return mark_safe(''.join([field.header_widget.render() for field in self.get_fields()]))

    def render_rows(self):
        rows_html = ""
        for row in self.data:
            row_html = ""
            for field in self.get_fields():
                if hasattr(field.cell_widget, 'render'):
                    try:
                        cell_html = field.cell_widget.render(row=row, request=self.request)
                    except TypeError:
                        cell_html = field.cell_widget.render(row)
                else:
                    cell_html = str(row)
                row_html += cell_html
            rows_html += f'<tr class="hover:bg-gray-50 dark:hover:bg-gray-900/50">{row_html}</tr>'

        return mark_safe(rows_html)

    def render(self):
        return format_html(
            """
            <table class="min-w-full whitespace-nowrap align-middle text-sm">
                <thead>
                    <tr>
                        {}
                    </tr>
                </thead>
                <tbody>
                    {}
                </tbody>
            </table>
            """,
            self.render_header(),
            self.render_rows()
        )
    
    @classmethod
    def from_model(cls, model, fields=None, exclude=None, extra_fields=None, meta_attrs=None):
        _declared_fields = {}

        if fields is None:
            fields = [f.name for f in model._meta.get_fields() if f.concrete and not f.auto_created]

        for field_name in fields:
            if exclude and field_name in exclude:
                continue
            field_obj = model._meta.get_field(field_name)
            _declared_fields[field_name] = TableField.from_model_field(field_obj)

        default_meta_attrs = {
            "model": model,
            "fields": fields,
            "exclude": exclude or [],
            "extra_fields": extra_fields or [],
        }

        if meta_attrs:
            default_meta_attrs.update(meta_attrs)

        Meta = type("Meta", (), default_meta_attrs)

        table_class = type(
            f"{model.__name__}Table",
            (cls,),
            {
                "_declared_fields": _declared_fields,
                "Meta": Meta,
            }
        )

        return table_class