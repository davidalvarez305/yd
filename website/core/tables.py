from django.utils.html import format_html
from django.utils.safestring import mark_safe

class ModelTableWidget:
    def __init__(self):
        self.model = None

class TableCellWidget:
    def __init__(self, data=None):
        self.data = data or {}

    def get_value(self, obj):
        value_func = self.data.get("value_func")
        value = self.data.get("value")

        if value_func:
            return value_func(obj)
        elif value:
            attrs = value.split(".")
            for attr in attrs:
                obj = getattr(obj, attr, None)
                if obj is None:
                    break
            return obj
        return None

    def render(self, row, **kwargs):
        value = self.get_value(row)
        return format_html('<td class="p-3 text-center">{}</td>', value)

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
        self.cell_widget = cell_widget or TableCellWidget()

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