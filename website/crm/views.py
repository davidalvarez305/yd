from django.http import HttpResponseNotAllowed
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import DetailView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render

from website import settings
from communication.models import Message
from core.models import LeadStatus, Lead, User, Service
from core.forms import ServiceForm, UserForm
from crm.forms import LeadForm, LeadFilterForm, CocktailForm, EventForm, LeadMarketingForm
from crm.models import Lead, Cocktail, Event
from marketing.models import LeadMarketing
from core.enums import AlertHTTPCodes, AlertStatus
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
        context['js_files'] += ['js/nav.js', 'js/main.js', 'js/modal.js']
        return context

class CRMBaseListView(LoginRequiredMixin, CRMContextMixin, ListView):
    filter_form_class = None
    create_form_class = None
    paginate_by = 10
    context_object_name = None

    def get_filter_form_class(self):
        return self.filter_form_class

    def get_create_form_class(self):
        return self.create_form_class

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
        context['js_files'] += ['js/pagination.js', 'js/filter.js']

        if hasattr(self, 'filter_form'):
            context['filter_form'] = self.filter_form
        elif self.filter_form_class:
            context['filter_form'] = self.filter_form_class()

        if self.create_form_class:
            context['create_form'] = self.create_form_class()

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
    trigger_alert = True

    def get_success_url(self):
        return self.success_url or reverse_lazy(f"{self.model._meta.model_name}_list")
    
    def alert(self, request, message, status: AlertStatus):
        template = 'core/success_alert.html' if status == AlertStatus.SUCCESS else 'core/error_alert.html'
        
        status_code = AlertHTTPCodes.get_http_code(status)

        return render(request, template_name=template, context={'message': message}, status=status_code)

    def post(self, request, *args, **kwargs):
        if not self.trigger_alert:
            return super().post(request, *args, **kwargs)

        self.object = self.get_object()
        form = self.get_form()

        if form.is_valid():
            try:
                form.instance.pk = self.object.pk
                form.save()
                return self.alert(request, "Successfully updated!", AlertStatus.SUCCESS)
            except Exception as e:
                print(f'Error updateing: {e}')
                return self.alert(request, "An unexpected error occurred while saving.", AlertStatus.INTERNAL_ERROR)
        else:
            return self.alert(request, "Form validation failed. Please correct the errors and try again.", AlertStatus.BAD_REQUEST)

class CRMBaseDeleteView(LoginRequiredMixin, CRMContextMixin, DeleteView):
    success_url = None

    def get_success_url(self):
        return self.success_url or reverse_lazy(f"{self.model._meta.model_name}_list")
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return redirect(self.get_success_url())

class CRMBaseDetailView(LoginRequiredMixin, CRMContextMixin, DetailView):
    success_url = None
    form_class = None

    def get_success_url(self):
        """
        Returns the success URL after viewing the details. 
        You can override this if you want to redirect to a custom URL.
        Defaults to a model's list page.
        """
        return self.success_url or reverse_lazy(f"{self.model._meta.model_name}_list")

    def get_context_data(self, **kwargs):
        """
        Add additional context to the template. 
        The object is added under `context_object_name`, either default or overridden.
        If a form_class is defined, include a form instance in context.
        """
        context = super().get_context_data(**kwargs)

        if not self.context_object_name:
            self.context_object_name = self.model._meta.model_name.lower()

        obj = self.get_object()

        if self.form_class:
            context['form'] = self.form_class(instance=obj)

        return context

class LeadListView(CRMBaseListView):
    model = Lead
    template_name = 'crm/lead_list.html'
    filter_form_class = LeadFilterForm

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.exclude(lead_status_id=ARCHIVED_LEAD_STATUS_ID)

class LeadUpdateView(CRMBaseUpdateView):
    model = Lead
    form_class = LeadForm
    trigger_alert = True

class LeadDetailView(CRMBaseDetailView):
    model = Lead
    template_name = 'crm/lead_detail.html'
    form_class = LeadForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        lead = self.object

        context['lead_marketing_form'] = LeadMarketingForm(instance=LeadMarketing.objects.filter(lead=lead).first())

        return context

class LeadMarketingUpdateView(CRMBaseUpdateView):
    model = LeadMarketing
    form_class = LeadMarketingForm

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        if form.is_valid():
            try:
                form.instance.lead = self.object.lead
                form.save()
                return self.alert(request, "Marketing info updated successfully.", AlertStatus.SUCCESS)
            except Exception as e:
                print(f"Unexpected error occurred: {e}")
                return self.alert(request, "An unexpected error occurred. Please try again.", AlertStatus.INTERNAL_ERROR)
        else:
            return self.alert(request, "There was a problem updating the marketing info. Please check the form.", AlertStatus.BAD_REQUEST)

class LeadArchiveView(CRMBaseUpdateView):
    model = Lead
    fields = []

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.lead_status = LeadStatus.objects.get(lead_status_id=ARCHIVED_LEAD_STATUS_ID)
        self.object.save()

        query_params = request.GET.urlencode()
        redirect_url = f"{reverse('lead_list')}?{query_params}" if query_params else reverse('lead_list')

        return redirect(redirect_url)
    
class CocktailListView(CRMBaseListView):
    model = Cocktail
    create_form_class = CocktailForm

class CocktailCreateView(CRMBaseCreateView):
    model = Cocktail
    form_class = CocktailForm

class CocktailUpdateView(CRMBaseUpdateView):
    model = Cocktail
    form_class = CocktailForm

class CocktailDetailView(CRMBaseDetailView):
    model = Cocktail
    form_class = CocktailForm

class CocktailDeleteView(CRMBaseDeleteView):
    model = Cocktail
    form_class = CocktailForm
    
class ServiceListView(CRMBaseListView):
    model = Service
    create_form_class = ServiceForm
    template_name = 'crm/service_list.html'

class ServiceCreateView(CRMBaseCreateView):
    model = Service
    form_class = ServiceForm

class ServiceUpdateView(CRMBaseUpdateView):
    model = Service
    form_class = ServiceForm

class ServiceDetailView(CRMBaseDetailView):
    model = Service
    form_class = ServiceForm
    template_name = 'crm/service_detail.html'

class ServiceDeleteView(CRMBaseDeleteView):
    model = Service
    form_class = ServiceForm
    
class UserListView(CRMBaseListView):
    model = User
    create_form_class = UserForm
    template_name = 'crm/user_list.html'

class UserCreateView(CRMBaseCreateView):
    model = User
    form_class = UserForm

class UserUpdateView(CRMBaseUpdateView):
    model = User
    form_class = UserForm

class UserDetailView(CRMBaseDetailView):
    model = User
    form_class = UserForm
    template_name = 'crm/user_detail.html'

class UserDeleteView(CRMBaseDeleteView):
    model = User
    form_class = UserForm
    
class EventListView(CRMBaseListView):
    model = Event
    create_form_class = EventForm

class EventCreateView(CRMBaseCreateView):
    model = Event
    form_class = EventForm

class EventUpdateView(CRMBaseUpdateView):
    model = Event
    form_class = EventForm

class EventDetailView(CRMBaseDetailView):
    model = Event
    form_class = EventForm

class EventDeleteView(CRMBaseDeleteView):
    model = Event
    form_class = EventForm