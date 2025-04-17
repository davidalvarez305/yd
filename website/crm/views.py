from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import DetailView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.db import connection
from django.core.paginator import Paginator
from django.shortcuts import redirect

from urllib.parse import urlencode

from website import settings
from core.views import BaseView
from communication.models import Message
from core.models import User, Lead
from crm.forms import LeadForm, LeadFilterForm
from crm.models import Lead
from website.settings import ARCHIVED_LEAD_STATUS_ID
from communication.models import Message

class CRMContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "assumed_base_hours_for_per_person_pricing": settings.ASSUMED_BASE_HOURS,
            "unread_messages": Message.objects.filter(is_read=False).count(),
        })
        context.setdefault('js_files', [])
        context['js_files'] += ['js/nav.js', 'js/main.js']
        return context

class CRMBaseListView(LoginRequiredMixin, CRMContextMixin, ListView):
    filter_form_class = None
    paginate_by = 10
    context_object_name = None

    def get_filter_form_class(self):
        return self.filter_form_class

    def get_queryset(self):
        queryset = self.model.objects.all()

        filter_form_class = self.get_filter_form_class()
        if filter_form_class:
            self.filter_form = filter_form_class(self.request.GET)

            if self.filter_form.is_valid():
                filters = {
                    field_name: field_value
                    for field_name, field_value in self.filter_form.cleaned_data.items()
                    if field_value not in [None, '']
                }
                queryset = queryset.filter(**filters)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if not self.context_object_name:
            self.context_object_name = f"{self.model._meta.model_name}s"

        context[self.context_object_name] = context.get('object_list')

        context.setdefault('js_files', [])
        context['js_files'] += ['js/pagination.js', 'js/filter.js', 'js/modal.js']

        if hasattr(self, 'filter_form'):
            context['form'] = self.filter_form
        elif self.filter_form_class:
            context['form'] = self.filter_form_class()

        return context

class CRMBaseCreateView(LoginRequiredMixin, CRMContextMixin, CreateView):
    success_url = None

    def get_success_url(self):
        return self.success_url or reverse_lazy(f"{self.model._meta.model_name}_list")

    def get_template_names(self):
        """
        Dynamically assigns the template name based on the model name.
        """
        model_name = self.model._meta.model_name
        return [f"{model_name}_form.html"]


class CRMBaseUpdateView(LoginRequiredMixin, CRMContextMixin, UpdateView):
    success_url = None

    def get_success_url(self):
        return self.success_url or reverse_lazy(f"{self.model._meta.model_name}_list")

    def get_template_names(self):
        """
        Dynamically assigns the template name based on the model name.
        """
        model_name = self.model._meta.model_name
        return [f"{model_name}_form.html"]


class CRMBaseDeleteView(LoginRequiredMixin, CRMContextMixin, DeleteView):
    success_url = None

    def get_success_url(self):
        return self.success_url or reverse_lazy(f"{self.model._meta.model_name}_list")

class CRMBaseDetailView(LoginRequiredMixin, CRMContextMixin, DetailView):
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

class LeadListView(CRMBaseListView):
    model = Lead
    template_name = 'crm/lead_list.html'
    filter_form_class = LeadFilterForm

class LeadUpdateView(CRMBaseUpdateView):
    form_class = LeadForm

class LeadDetailView(CRMBaseDetailView):
    model = Lead

class LeadDeleteView(CRMBaseDeleteView):
    model = Lead

class LeadArchiveView(CRMBaseUpdateView):
    model = Lead

    def post(self, request, *args, **kwargs):
        Lead.objects.update(status_id=ARCHIVED_LEAD_STATUS_ID)

        query_params = request.GET.urlencode()
        redirect_url = f"{reverse('lead_list')}?{query_params}" if query_params else reverse('lead_list')

        return redirect(redirect_url)