from django.utils.timezone import now
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404

from website.website import settings
from website.core.views import BaseView

class CRMBaseView(LoginRequiredMixin, BaseView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Additional CRM-specific context
        context.update({
            "assumed_base_hours_for_per_person_pricing": settings.ASSUMED_BASE_HOURS,
        })

        # Fetch unread messages count
        context["unread_messages"] = Message.objects.filter(is_read=False).count()

        # Get user's phone number
        user = get_object_or_404(User, user=self.request.user)
        context["crm_user_phone_number"] = user.phone_number

        return context

class CRMBaseListView(CRMBaseView, ListView):
    """
    A base list view class for CRM views. Automatically injects filters based on form.
    This class can be extended for more complex filtering logic as needed.
    """
    filter_form_class = None
    paginate_by = 10

    def get_filter_form_class(self):
        """
        Returns the filter form class. You can override this in specific views.
        """
        if self.filter_form_class:
            return self.filter_form_class
        return None

    def get_queryset(self):
        """
        Automatically applies filters based on the form.
        You can override this method for more complex filtering logic.
        """
        queryset = super().get_queryset()

        filter_form_class = self.get_filter_form_class()
        if filter_form_class:
            filter_form = filter_form_class(self.request.GET)

            if filter_form.is_valid():
                filters = {}

                for field_name, field_value in filter_form.cleaned_data.items():
                    if field_value:
                        filters[field_name] = field_value

                queryset = queryset.filter(**filters)

        return queryset

    def get_context_data(self, **kwargs):
        """
        Overrides the get_context_data method to inject both CRM-specific data
        and JavaScript files for all ListViews that inherit from this class.
        """
        context = super().get_context_data(**kwargs)

        context['js_files'] = [
            'main.js',
            'pagination.js',
            'filter.js',
            'modal.js'
        ]
        
        return context


class IndexView(CRMBaseView):
    template_name = "index.html"