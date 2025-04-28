from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.template.context_processors import csrf

from .utils import deep_getattr
from .widgets import DeleteButton, ViewButton

# Example Use
""" 
class CocktailTable(Table):
    class Meta:
        model = Cocktail
        fields = ['name']

CocktailTable = Table.from_model(Cocktail, exclude=["created_at", "updated_at"])

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

class TableCellWidget:
    def __init__(self, data=None):
        self.data = data or {}

    def get_value(self, obj):
        value = self.data.get("value")
        if value:
            return deep_getattr(obj, value)
        return None

    def get_attrs(self, row=None):
        attrs = self.data.get("attrs", {})
        parts = []
        for key, value in attrs.items():
            if isinstance(value, str) and row:
                try:
                    value = value.format(**row.__dict__)
                except Exception:
                    pass
            parts.append(f'{key}="{value}"')
        return " ".join(parts)

    def render(self, row, **kwargs):
        value = self.get_value(row)
        attrs = self.get_attrs(row)
        return format_html('<td {} class="p-3 text-center">{}</td>', mark_safe(attrs), value)

class TemplateCellWidget:
    def __init__(self, template=None, context=None, data=None):
        super().__init__()
        self.template = template
        self.context = context or {}
        self.data = data or {}

    def resolve_context(self, row):
        final_context = {}
        for key, value in self.context.items():
            if isinstance(value, str) and "{" in value and "}" in value:
                import re
                matches = re.findall(r"{(.*?)}", value)
                for match in matches:
                    nested_value = deep_getattr(row, match)
                    if nested_value is not None:
                        value = value.replace(f"{{{match}}}", str(nested_value))
            final_context[key] = value
        return final_context

    def render(self, value=None, row=None, request=None):
        context = self.resolve_context(row)

        if request and self.data.get("csrf", False):
            context.update(csrf(request))

        return mark_safe(render_to_string(self.template, context))

class TableHeaderWidget:
    def __init__(self, label):
        self.label = label

    def render(self):
        return format_html(
            '<th class="bg-gray-100/75 px-3 py-4 text-center font-semibold text-gray-900 dark:bg-gray-700/25 dark:text-gray-50">{}</th>',
            self.label.title()
        )

class TableField:
    def __init__(self, name=None, label=None, header_widget=None, cell_widget=None):
        self.name = name
        self.label = label or name.replace("_", " ").title()
        self.header_widget = header_widget or TableHeaderWidget(self.label)
        self.cell_widget = cell_widget or self.build_default_cell_widget()

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

        if "delete" in extra_fields:
            _declared_fields["delete"] = TableField(
                name="Delete",
                cell_widget=DeleteButton(pk=pk, url=delete_url)
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
    def from_model(cls, model, fields=None, exclude=None):
        _declared_fields = {}

        if fields is None:
            fields = [f.name for f in model._meta.get_fields() if f.concrete and not f.auto_created]

        for field_name in fields:
            if exclude and field_name in exclude:
                continue
            field_obj = model._meta.get_field(field_name)
            _declared_fields[field_name] = TableField.from_model_field(field_obj)

        table_class = type(
            f"{model.__name__}Table",
            (cls,),
            {
                "_declared_fields": _declared_fields,
                "Meta": type("Meta", (), {"model": model}),
            }
        )
        return table_class