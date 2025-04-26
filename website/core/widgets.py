from django.forms.widgets import CheckboxInput
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string

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
    
class ViewButtonWidget:
    def __init__(self, detail_url_name=None, pk=0):
        self.detail_url_name = detail_url_name
        self.pk = pk

    def get_pk(self, row):
        if isinstance(self.pk, int):
            return row[self.pk]
        elif isinstance(row, dict):
            return row.get(self.pk)
        else:
            return getattr(row, self.pk, None)

    def render(self, value=None, row=None, detail_url_name=None):
        url_name = detail_url_name or self.detail_url_name
        if not url_name:
            raise ValueError("detail_url_name must be provided")
        context = {
            "pk": self.get_pk(row),
            "detail_url_name": url_name,
        }
        return mark_safe(render_to_string("components/view_button_widget.html", context))


class DeleteButtonWidget:
    def __init__(self, delete_url_name=None, pk=0):
        self.delete_url_name = delete_url_name
        self.pk = pk

    def get_pk(self, row):
        if isinstance(self.pk, int):
            return row[self.pk]
        elif isinstance(row, dict):
            return row.get(self.pk)
        else:
            return getattr(row, self.pk, None)

    def render(self, value=None, row=None, delete_url_name=None):
        url_name = delete_url_name or self.delete_url_name
        if not url_name:
            raise ValueError("delete_url_name must be provided")
        context = {
            "pk": self.get_pk(row),
            "delete_url_name": url_name,
        }
        return mark_safe(render_to_string("components/delete_button_widget.html", context))
