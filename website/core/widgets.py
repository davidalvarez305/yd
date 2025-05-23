from django import forms
from django.forms.widgets import CheckboxInput
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.template.context_processors import csrf

from .utils import deep_getattr

# Form Widgets
class ToggleSwitchWidget(CheckboxInput):
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'peer sr-only',
        }
        if attrs:
            default_attrs.update(attrs)
        self.attrs = default_attrs

    def render(self, name, value, attrs=None, renderer=None):
        if attrs:
            self.attrs.update(attrs)

        field_id = self.attrs.get('id', name)
        message = self.attrs.get('message', '')

        checkbox = super().render(name, value, attrs, renderer)

        html = f"""
        <label for="{field_id}" class="group relative inline-flex items-center gap-3">
            {checkbox}
            <span
                class="hover:cursor-pointer relative h-7 w-12 flex-none rounded-full bg-gray-300 transition-all duration-150 ease-out before:absolute before:left-1 before:top-1 before:size-5 before:rounded-full before:bg-white before:transition-transform before:duration-150 before:ease-out before:content-[''] peer-checked:bg-primary-500 peer-checked:before:translate-x-full peer-focus:ring peer-focus:ring-primary-500/50 peer-focus:ring-offset-2 peer-focus:ring-offset-white peer-disabled:cursor-not-allowed peer-disabled:opacity-75 dark:bg-gray-700 dark:peer-checked:bg-primary-500 dark:peer-focus:ring-offset-gray-900">
            </span>
            <span class="font-medium">{message}</span>
        </label>
        """
        return mark_safe(html)

    def check_test(self, value):
        """
        Determine if the checkbox should be checked based on the value.
        If value is True, the checkbox is checked; otherwise, it is unchecked.
        """
        return value is True or value == 'on'

class TableCellWidget:
    def __init__(self, data=None):
        self.data = data or {}

    def get_value(self, obj):
        value = self.data.get("value")
        if value:
            if callable(value):
                return value(obj)
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

class PriceCellWidget(TableCellWidget):
    def render(self, value=None, row=None, request=None):
        if value is None:
            value = getattr(row, self.data.get("value"), None)
        if value is not None:
            return format_html(f"<td>${value:.2f}</td>")
        return "<td>$0.00</td>"

def ViewButton(pk="id", url=None):
    return TemplateCellWidget(
        template="components/view_button_widget.html",
        context={
            "pk": f"{{{pk}}}",
            "view_lookup_name": url
        }
    )

def DeleteButton(pk="id", url=None):
    return TemplateCellWidget(
        template="components/delete_button_widget.html",
        context={
            "pk": f"{{{pk}}}",
            "view_lookup_name": url
        },
        data={"csrf": True}
    )

class AutocompleteSelect(forms.SelectMultiple):
    template_name = 'components/autocomplete_select.html'

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        option['attrs']['class'] = (
            "group flex cursor-pointer items-center justify-between gap-2 "
            "rounded-lg px-3 text-sm text-gray-600 hover:bg-gray-100 "
            "hover:text-gray-950 dark:text-gray-300 dark:hover:bg-gray-800 "
            "dark:hover:text-white"
        )
        return option