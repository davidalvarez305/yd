from django.utils.timezone import now
from django.http import HttpResponseRedirect
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404

from website import settings
from core.views import BaseView
from communication.models import Message
from core.models import User

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
    context_object_name = None  # Default is None, which will use a pluralized model name

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

    def get_template_names(self):
        """
        Dynamically assigns the template name based on the model name.
        """
        model_name = self.model._meta.model_name
        return [f"{model_name}_list.html"]

    def get_context_data(self, **kwargs):
        """
        Overrides the get_context_data method to inject both CRM-specific data
        and JavaScript files for all ListViews that inherit from this class.
        """
        context = super().get_context_data(**kwargs)

        # Set the default context object name to the plural version of the model name
        if not self.context_object_name:
            self.context_object_name = f"{self.model._meta.model_name}s"  # Pluralize model name

        # Add the object list to context with the context name (either the default or custom)
        context[self.context_object_name] = self.get_queryset()

        # Inject the JavaScript files into the context for the view
        context['js_files'] = [
            'pagination.js',
            'filter.js',
            'modal.js'
        ]
        
        return context

class CRMBaseCreateView(CRMBaseView, CreateView):
    success_url = None

    def get_success_url(self):
        return self.success_url or reverse_lazy(f"{self.model._meta.model_name}_list")

    def get_template_names(self):
        """
        Dynamically assigns the template name based on the model name.
        """
        model_name = self.model._meta.model_name
        return [f"{model_name}_form.html"]


class CRMBaseUpdateView(CRMBaseView, UpdateView):
    success_url = None

    def get_success_url(self):
        return self.success_url or reverse_lazy(f"{self.model._meta.model_name}_list")

    def get_template_names(self):
        """
        Dynamically assigns the template name based on the model name.
        """
        model_name = self.model._meta.model_name
        return [f"{model_name}_form.html"]


class CRMBaseDeleteView(CRMBaseView, DeleteView):
    success_url = None

    def get_success_url(self):
        return self.success_url or reverse_lazy(f"{self.model._meta.model_name}_list")

class CRMBaseDetailView(CRMBaseView, DetailView):
    success_url = None

    def get_success_url(self):
        """
        Returns the success URL after viewing the details. 
        You can override this if you want to redirect to a custom URL.
        Defaults to a model's list page.
        """
        return self.success_url or reverse_lazy(f"{self.model._meta.model_name}_list")

    def get_template_names(self):
        """
        Dynamically assigns the template name based on the model name.
        The template name will be: <model_name>_detail.html
        """
        model_name = self.model._meta.model_name
        return [f"{model_name}_detail.html"]
    
    def get_context_data(self, **kwargs):
        """
        Add additional context to the template. 
        The object is added under `context_object_name`, either default or overridden.
        """
        context = super().get_context_data(**kwargs)

        if not self.context_object_name:
            self.context_object_name = self.model._meta.model_name.lower()

        context[self.context_object_name] = self.get_object()

        return context