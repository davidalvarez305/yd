from django import forms
from django.forms.widgets import CheckboxInput
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.utils.html import format_html, escape
from django.template.context_processors import csrf

from core.mixins import ContextResolverMixin

from .utils import deep_getattr

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
        self.is_html = self.data.get("is_html", False)

    def get_value(self, obj):
        value = self.data.get("value")
        if value:
            if callable(value):
                return value(obj)
            return deep_getattr(obj, value)
        return None

    def get_attrs(self, row=None):
        attrs = self.data.get("attrs", {})
        formatted_attrs = {}

        for key, value in attrs.items():
            if isinstance(value, str) and row:
                try:
                    value = value.format(**row.__dict__)
                except Exception:
                    pass
            formatted_attrs[key] = value

        # Add default class if not provided
        if "class" not in formatted_attrs:
            formatted_attrs["class"] = "p-3 text-center"

        parts = [f'{key}="{value}"' for key, value in formatted_attrs.items()]
        return " ".join(parts)

    def render(self, row, request):
        value = self.get_value(row)
        attrs = self.get_attrs(row)

        if not self.is_html:
            value = escape(value)
        else:
            value = mark_safe(value)

        return format_html('<td {}>{}</td>', mark_safe(attrs), value)

class TemplateCellWidget:
    def __init__(self, template=None, context=None, data=None, context_resolver=None):
        self.template = template
        self.context = context or {}
        self.data = data or {}
        self.context_resolver = context_resolver

    def resolve_context(self, row):
        if self.context_resolver:
            return self.context_resolver(row)

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

        final_context["row"] = row
        return final_context

    def render(self, row=None, request=None):
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
    def render(self, row=None, request=None):
        value = getattr(row, self.data.get("value"), None)
        if value is not None:
            return format_html(f"<td>${value:.2f}</td>")
        return "<td>$0.00</td>"

def ViewButton(pk, view_name):
    if not pk or not view_name:
        raise TypeError('Missing primary key or view name in view button.')

    return TemplateCellWidget(
        template="components/view_button_widget.html",
        context={
            "pk": f"{{{pk}}}",
            "view_lookup_name": view_name
        }
    )

class DeleteButton(TemplateCellWidget, ContextResolverMixin):
    def __init__(self, view_name, attrs=None, context=None, context_resolver=None):
        self.view_name = view_name
        self.attrs = attrs or {}

        base_context = {
            "attrs": self.attrs,
        }

        TemplateCellWidget.__init__(
            self,
            template="components/delete_button_widget.html",
            context=base_context,
            data={},
            context_resolver=context_resolver
        )

        ContextResolverMixin.__init__(
            self,
            context=base_context,
            context_resolver=context_resolver
        )