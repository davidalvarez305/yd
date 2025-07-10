from django import forms
from django.forms.widgets import CheckboxInput
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.utils.html import format_html, escape
from django.template.context_processors import csrf

from core.mixins import ContextResolverMixin
from website import settings
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

class BoxedCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    template_name = "components/boxed_checkbox_multiple_select_widget.html"
    option_template_name = "components/boxed_checkbox_multiple_select_option.html"

    def __init__(self, attrs=None):
        default_attrs = {"class": "peer sr-only"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['option_template_name'] = self.option_template_name
        return context

class ContainedCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    template_name = "components/contained_checkbox_multiple_select_widget.html"
    option_template_name = "components/contained_checkbox_multiple_select_option.html"

    def __init__(self, attrs=None):
        default_attrs = {"class": "peer sr-only"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['option_template_name'] = self.option_template_name
        return context
    
# Table Widgets
class TableHeaderWidget:
    def __init__(self, label):
        self.label = label

    def render(self):
        return format_html(
            '<th class="bg-gray-100/75 px-3 py-4 text-center font-semibold text-gray-900 dark:bg-gray-700/25 dark:text-gray-50">{}</th>',
            self.label.title()
        )

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

class TemplateCellWidget(ContextResolverMixin):
    def __init__(self, template=None, context=None, data=None, context_resolver=None):
        self.template = template
        self.data = data or {}

        super().__init__(context=context, context_resolver=context_resolver)

    def render(self, row=None, request=None):
        context = self.resolve_context(base=row, request=request)

        if request and self.data.get("csrf", False):
            context.update(csrf(request))

        return mark_safe(render_to_string(self.template, context))

class PriceCellWidget(TableCellWidget):
    def render(self, row=None, request=None):
        value = getattr(row, self.data.get("value"), None)
        if value is not None:
            return format_html(f"<td>${value:.2f}</td>")
        return "<td>$0.00</td>"

class AudioWidget(TableCellWidget):
    def render(self, row=None, request=None):
        object_key = self.data.get('value')
        if object_key:
            media_path = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', settings.MEDIA_URL)
            src = media_path + object_key(row)

            return f"""
                <td>
                    <audio controls class="w-full rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-200">
                        <source src="{src}" type="audio/mpeg">
                        Your browser does not support the audio element.
                    </audio>
                </td>
            """
        return "<td></td>"

class ViewButton(TemplateCellWidget):
    def __init__(self, context={}, context_resolver=None):
        super().__init__(
            template="components/view_button_widget.html",
            context=context,
            data={},
            context_resolver=context_resolver
        )

class DeleteButton(TemplateCellWidget):
    def __init__(self, context={}, context_resolver=None):
        super().__init__(
            template="components/delete_button_widget.html",
            context=context,
            data={"csrf": True},
            context_resolver=context_resolver
        )