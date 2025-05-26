from django.http import HttpResponse
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import DetailView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F
from django.utils.timezone import now
from django.http import HttpResponseRedirect

from website import settings
from core.models import CallTrackingNumber, EventCocktail, EventStaff, HTTPLog, LeadNote, Message, PhoneCall, Message, Visit
from communication.forms import MessageForm, OutboundPhoneCallForm, PhoneCallForm
from core.models import LeadStatus, Lead, User, Service, Cocktail, Event, LeadMarketing
from core.forms import ServiceForm, UserForm
from crm.forms import EventCocktailForm, EventStaffForm, HTTPLogFilterForm, CallTrackingNumberForm, LeadForm, LeadFilterForm, CocktailForm, EventForm, LeadMarketingForm, LeadNoteForm, VisitFilterForm, VisitForm
from core.enums import AlertStatus
from core.mixins import AlertMixin
from crm.tables import CocktailTable, EventCocktailTable, EventStaffTable, MessageTable, PhoneCallTable, ServiceTable, EventTable, UserTable, VisitTable
from core.tables import Table
from core.utils import format_phone_number, is_mobile
from website.settings import ARCHIVED_LEAD_STATUS_ID

class CRMContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": settings.COMPANY_NAME,
            "meta_description": "YD Cocktails CRM",
            "site_name": settings.SITE_NAME,
            "phone_number": format_phone_number(settings.COMPANY_PHONE_NUMBER),
            "current_year": now().year,
            "company_name": settings.COMPANY_NAME,
            "page_path": f"{settings.ROOT_DOMAIN}{self.request.path}",
            "is_mobile": is_mobile(self.request.META.get('HTTP_USER_AGENT', '')),
            "assumed_base_hours_for_per_person_pricing": settings.ASSUMED_BASE_HOURS,
            "unread_messages": Message.objects.filter(is_read=False).count(),
        })
        context.setdefault('js_files', [])
        context['js_files'] += ['js/nav.js', 'js/main.js', 'js/modal/ModalHelper.js']
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
                model_fields = {f.name for f in self.model._meta.get_fields()}

                filters = {
                    field_name: field_value
                    for field_name, field_value in self.filter_form.cleaned_data.items()
                    if field_name in model_fields and field_value not in [None, '']
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

class CRMBaseUpdateView(LoginRequiredMixin, CRMContextMixin, AlertMixin, UpdateView):
    success_url = None
    trigger_alert = False

    def get_success_url(self):
        return self.success_url or reverse_lazy(f"{self.model._meta.model_name}_list")
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        if form.is_valid():
            try:
                form.save()

                if not self.trigger_alert:
                    return redirect(self.get_success_url())

                return self.alert(request, "Successfully updated!", AlertStatus.SUCCESS)
            except Exception as e:
                print(f'Error updating: {e}')
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

class CRMBaseCreateView(LoginRequiredMixin, CRMContextMixin, CreateView):
    success_url = None
    trigger_alert = False

    def get_success_url(self):
        return self.success_url or reverse_lazy(f"{self.model._meta.model_name}_list")

    def get_template_names(self):
        """
        Dynamically assigns the template name based on the model name.
        """
        model_name = self.model._meta.model_name
        return [f"crm/{model_name}_form.html"]
    
    def form_valid(self, form):
        response = super().form_valid(form)

        """ if self.trigger_alert:
            return self.alert(self.request, "Successfully created!", AlertStatus.SUCCESS) """

        if self.request.headers.get('HX-Request') == 'true':
            success_url = self.get_success_url()
            return HttpResponse(status=200, headers={'HX-Redirect': success_url})

        return response

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

class CRMDetailTemplateView(CRMBaseDetailView):
    template_name = "crm/base_detail.html"
    context_object_name = "object"
    update_url = None
    pk = None

    def get_update_url(self):
        if self.update_url:
            return self.update_url
        model_name = self.model._meta.model_name
        return f"{model_name}_update"

    def get_pk(self):
        if hasattr(self, "pk") and self.pk is not None:
            return self.pk
        if hasattr(self, "object") and self.object is not None:
            return getattr(self.object, self.object._meta.pk.name)
        raise ValueError("Cannot determine PK: neither pk nor object is set.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update_url"] = self.get_update_url()
        context["pk"] = self.get_pk()
        return context

class CRMCreateTemplateView(CRMBaseCreateView):
    template_name = None
    create_url = None

    def get_template_names(self):
        if self.template_name:
            return [self.template_name]
        return ["crm/base_create.html"]

    def get_create_url(self):
        if self.create_url:
            return self.create_url
        model_name = self.model._meta.model_name
        return f"{model_name}_create"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["create_url"] = self.get_create_url()
        return context

class CRMTableView(CRMBaseListView):
    template_name = "crm/base_table.html"
    context_object_name = "table"
    table_class = None
    create_url = None
    detail_url = None
    delete_url = None
    show_add_button = True

    def get_create_url(self):
        if self.create_url:
            return self.create_url
        model_name = self.model._meta.model_name
        return f"{model_name}_create"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        table = self.table_class(self.object_list)
        table.request = self.request

        context["table"] = table
        context["create_url"] = self.get_create_url()
        context["show_add_button"] = self.show_add_button
        return context

class LeadListView(CRMBaseListView):
    model = Lead
    template_name = 'crm/lead_list.html'
    filter_form_class = LeadFilterForm

    def get_queryset(self):
        queryset = super().get_queryset()
        
        search = self.request.GET.get('search')
        
        if search:
            search_query = SearchQuery(search, search_type='plain')

            queryset = queryset.annotate(
                rank=SearchRank(F('search_vector'), search_query)
            ).filter(search_vector=search_query)

            print(queryset)
            
            queryset = queryset.order_by('-rank')

        else:
            queryset = queryset.exclude(lead_status_id=ARCHIVED_LEAD_STATUS_ID)
        
        return queryset

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
        
        context['chat_form'] = MessageForm(initial={
            'text_to': lead.phone_number,
            'text_from': self.request.user.phone_number,
        })

        context['outbound_call_form'] = OutboundPhoneCallForm(initial={
            'from_': self.request.user.phone_number,
            'to_': lead.phone_number
        })

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
    
class CocktailListView(CRMTableView):
    model = Cocktail
    table_class = CocktailTable

class CocktailCreateView(CRMCreateTemplateView):
    model = Cocktail
    form_class = CocktailForm

class CocktailUpdateView(CRMBaseUpdateView):
    model = Cocktail
    form_class = CocktailForm

class CocktailDetailView(CRMDetailTemplateView):
    model = Cocktail
    form_class = CocktailForm

class CocktailDeleteView(CRMBaseDeleteView):
    model = Cocktail
    form_class = CocktailForm
    
class ServiceListView(CRMTableView):
    model = Service
    table_class = ServiceTable

class ServiceCreateView(CRMCreateTemplateView):
    model = Service
    form_class = ServiceForm

class ServiceUpdateView(CRMBaseUpdateView):
    model = Service
    form_class = ServiceForm

class ServiceDetailView(CRMDetailTemplateView):
    model = Service
    form_class = ServiceForm

class ServiceDeleteView(CRMBaseDeleteView):
    model = Service
    form_class = ServiceForm
    
class UserListView(CRMTableView):
    model = User
    table_class = UserTable

class UserCreateView(CRMCreateTemplateView):
    model = User
    form_class = UserForm

class UserUpdateView(CRMBaseUpdateView):
    model = User
    form_class = UserForm

class UserDetailView(CRMDetailTemplateView):
    model = User
    form_class = UserForm

class UserDeleteView(CRMBaseDeleteView):
    model = User
    form_class = UserForm
    
class EventListView(CRMTableView):
    model = Event
    table_class = EventTable

class EventCreateView(CRMCreateTemplateView):
    model = Event
    form_class = EventForm

class EventUpdateView(CRMBaseUpdateView):
    model = Event
    form_class = EventForm
    trigger_alert = True

class EventDetailView(CRMDetailTemplateView):
    template_name = 'crm/event_internal_detail.html'
    context_object_name = 'event'
    model = Event
    form_class = EventForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        initial = { 'event': self.object }
        
        context.update({
            'cocktails': Cocktail.objects.all(),
            'event_cocktail_form': EventCocktailForm(initial=initial),
            'event_cocktail_table': EventCocktailTable(data=EventCocktail.objects.filter(event=self.object), request=self.request),
            'event_staff_form': EventStaffForm(initial=initial),
            'event_staff_table': EventStaffTable(data=EventStaff.objects.filter(event=self.object), request=self.request),
        })

        return context

class EventDeleteView(CRMBaseDeleteView):
    model = Event
    form_class = EventForm

class MessageListView(CRMTableView):
    model = Message
    table_class = MessageTable
    show_add_button = False

class MessageDetailView(CRMDetailTemplateView):
    model = Message
    form_class = MessageForm

class MessageUpdateView(CRMBaseUpdateView):
    model = Message
    form_class = MessageForm

class PhoneCallListView(CRMTableView):
    model = PhoneCall
    table_class = PhoneCallTable
    show_add_button = False

class PhoneCallDetailView(CRMDetailTemplateView):
    model = PhoneCall
    form_class = PhoneCallForm

class PhoneCallUpdateView(CRMBaseUpdateView):
    model = PhoneCall
    form_class = PhoneCallForm

class HTTPLogListView(CRMBaseListView):
    model = HTTPLog
    context_object_name = "logs"
    filter_form_class = HTTPLogFilterForm

class CallTrackingNumberListView(CRMTableView):
    model = CallTrackingNumber
    table_class = (
        Table.from_model(
            model=CallTrackingNumber,
            exclude=['call_tracking_number_id'],
            extra_fields=['view', 'delete'],
            meta_attrs={
                'pk': 'call_tracking_number_id',
            }
        )
    )

class CallTrackingNumberCreateView(CRMCreateTemplateView):
    model = CallTrackingNumber
    form_class = CallTrackingNumberForm

class CallTrackingNumberUpdateView(CRMBaseUpdateView):
    model = CallTrackingNumber
    form_class = CallTrackingNumberForm

class CallTrackingNumberDetailView(CRMDetailTemplateView):
    model = CallTrackingNumber
    form_class = CallTrackingNumberForm

class CallTrackingNumberDeleteView(CRMBaseDeleteView):
    model = CallTrackingNumber
    form_class = CallTrackingNumberForm

class VisitListView(CRMTableView):
    model = Visit
    table_class = VisitTable
    show_add_button = False

class VisitUpdateView(UpdateView):
    form_class = VisitForm
    model = Visit
    http_method_names = ['post']
    
    def form_valid(self, form):
        form.save()
        return HttpResponse("Updated")

class LeadNoteDetailView(CRMDetailTemplateView):
    model = LeadNote
    form_class = LeadNoteForm

class LeadNoteCreateView(CRMBaseCreateView):
    model = LeadNote
    form_class = LeadNoteForm

class LeadNoteUpdateView(CRMBaseUpdateView):
    model = LeadNote
    form_class = LeadNoteForm

class LeadNoteDeleteView(CRMBaseDeleteView):
    model = LeadNote
    form_class = LeadNoteForm

class LeadChatView(LoginRequiredMixin, CRMContextMixin, ListView):
    model = Message
    template_name = 'crm/messages.html'
    context_object_name = 'messages'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        leads = Lead.objects.all()
        context['leads'] = leads
        return context

class LeadChatMessagesView(LoginRequiredMixin, ListView):
    model = Message
    template_name = 'crm/lead_chat.html'
    context_object_name = 'lead'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lead = Lead.objects.filter(pk=self.kwargs.get('pk')).first()
        context['lead'] = lead
        context['chat_form'] = MessageForm(initial={
            'text_to': lead.phone_number,
            'text_from': self.request.user.phone_number,
        })
        return context

class CocktailOptionsListView(LoginRequiredMixin, ListView):
    model = Cocktail

    def get(self, request, *args, **kwargs):
        search = self.request.GET.get('search', '')

        cocktails = Cocktail.objects.filter(name__icontains=search)
        html = ''

        for cocktail in cocktails:
            html += f'''
            <option class="group flex cursor-pointer items-center justify-between gap-2 rounded-lg px-3 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-950 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-white" role="option" tabindex="-1" aria-selected="false">
                <div class="grow truncate py-2 font-medium">{cocktail.name}</div>
            </option>
            '''

        return HttpResponse(html)

class EventCocktailCreateView(CRMCreateTemplateView):
    model = EventCocktail
    form_class = EventCocktailForm

    def form_valid(self, form):
        self.object = form.save()

        event = self.object.event
        qs = EventCocktail.objects.filter(event=event)
        table = EventCocktailTable(data=qs, request=self.request)

        return HttpResponse(table.render())

class EventCocktailDeleteView(CRMBaseDeleteView):
    model = EventCocktail
    form_class = EventCocktailForm

    def get_success_url(self):
            return self.request.headers.get('Referer')


class EventStaffCreateView(CRMCreateTemplateView):
    model = EventStaff
    form_class = EventStaffForm

    def form_valid(self, form):
        self.object = form.save()

        event = self.object.event
        qs = EventStaff.objects.filter(event=event)
        table = EventStaffTable(data=qs, request=self.request)

        return HttpResponse(table.render())

class EventStaffDeleteView(CRMBaseDeleteView):
    model = EventStaff
    form_class = EventStaffForm

    def get_success_url(self):
            return self.request.headers.get('Referer')