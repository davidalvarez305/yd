from django.utils.html import format_html
from django.utils.safestring import mark_safe

from core.utils import deep_getattr

class ModelTableWidget:
    def __init__(self):
        self.model = None

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

class TableHeaderWidget:
    def __init__(self, label):
        self.label = label

    def render(self):
        return format_html(
            '<th class="bg-gray-100/75 px-3 py-4 text-center font-semibold text-gray-900 dark:bg-gray-700/25 dark:text-gray-50">{}</th>',
            self.label.title()
        )

class TableField:
    def __init__(self, name, label=None, header_widget=None, cell_widget=None):
        self.name = name
        self.label = label or name.replace("_", " ").title()
        self.header_widget = header_widget or TableHeaderWidget(self.label)
        self.cell_widget = cell_widget or self.build_default_cell_widget()

    def build_default_cell_widget(self):
        return TableCellWidget(data={"value": self.name})

class DeclarativeTableMeta(type):
    def __new__(cls, name, bases, attrs):
        declared_fields = {
            key: value for key, value in attrs.items()
            if isinstance(value, TableField)
        }

        new_class = super().__new__(cls, name, bases, attrs)

        meta = attrs.get('Meta', None)
        model = getattr(meta, 'model', None)
        include_fields = getattr(meta, 'fields', None)

        if model and include_fields:
            for field_name in include_fields:
                if field_name not in declared_fields:
                    field_obj = model._meta.get_field(field_name)
                    label = field_obj.verbose_name.title()
                    declared_fields[field_name] = TableField(name=field_name, label=label)

        new_class._declared_fields = declared_fields
        return new_class

class Table(metaclass=DeclarativeTableMeta):
    def __init__(self, data=None):
        self.data = data or []
        self.model = getattr(self.Meta, "model", None)

        for field in self.get_fields():
            widget = getattr(field, "cell_widget", None)
            if isinstance(widget, ModelTableWidget):
                widget.model = self.model

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