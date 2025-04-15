from django.forms.widgets import CheckboxInput
from django.utils.safestring import mark_safe

class ToggleSwitchWidget(CheckboxInput):
    def render(self, name, value, attrs, renderer=None):
        checkbox = super().render(name, value, attrs, renderer)
        html = f"""
        <label for="{attrs.get('id')}" class="group relative inline-flex items-center gap-3">
            {checkbox}
            <span
                class="hover:cursor-pointer relative h-7 w-12 flex-none rounded-full bg-gray-300 transition-all duration-150 ease-out before:absolute before:left-1 before:top-1 before:size-5 before:rounded-full before:bg-white before:transition-transform before:duration-150 before:ease-out before:content-[''] peer-checked:bg-primary-500 peer-checked:before:translate-x-full peer-focus:ring peer-focus:ring-primary-500/50 peer-focus:ring-offset-2 peer-focus:ring-offset-white peer-disabled:cursor-not-allowed peer-disabled:opacity-75 dark:bg-gray-700 dark:peer-checked:bg-primary-500 dark:peer-focus:ring-offset-gray-900">
            </span>
            <span class="font-medium">I consent to receiving text message notifications.</span>
        </label>
        """
        return mark_safe(html)