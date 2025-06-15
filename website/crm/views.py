from django.forms import ValidationError
from django.http import HttpResponse
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.views.generic import DetailView
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F
from django.utils.timezone import now

from website import settings
from core.models import CallTrackingNumber, CocktailIngredient, EventCocktail, EventShoppingList, EventShoppingListEntry, EventStaff, HTTPLog, Ingredient, LeadNote, LeadStatusEnum, Message, PhoneCall, Message, Quote, QuotePreset, QuoteService, StoreItem, Visit
from communication.forms import MessageForm, OutboundPhoneCallForm, PhoneCallForm
from core.models import LeadStatus, Lead, User, Service, Cocktail, Event, LeadMarketing
from core.forms import ServiceForm, UserForm
from crm.forms import QuickQuoteForm, QuoteForm, CocktailIngredientForm, EventCocktailForm, EventShoppingListForm, EventStaffForm, HTTPLogFilterForm, CallTrackingNumberForm, IngredientForm, LeadForm, LeadFilterForm, CocktailForm, EventForm, LeadMarketingForm, LeadNoteForm, QuotePresetForm, QuoteSendForm, QuoteServiceForm, StoreItemForm, VisitFilterForm, VisitForm
from core.enums import AlertStatus
from core.mixins import AlertMixin
from crm.tables import CocktailIngredientTable, CocktailTable, EventCocktailTable, EventStaffTable, IngredientTable, MessageTable, PhoneCallTable, QuotePresetTable, QuoteServiceTable, QuoteTable, ServiceTable, EventTable, StoreItemTable, UserTable, VisitTable
from core.tables import Table
from core.utils import format_phone_number, format_text_message, get_first_field_error, is_mobile
from website.settings import ARCHIVED_LEAD_STATUS_ID
from crm.utils import convert_to_item_quantity
from core.messaging import messaging_service

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
            "unread_messages": Message.objects.filter(is_read=False).count(),
        })
        context.setdefault('js_files', [])
        context['js_files'] += ['js/nav.js', 'js/main.js', 'js/modal/ModalHelper.js']
        return context

class CRMBaseView(LoginRequiredMixin, CRMContextMixin):
    success_url = None
    trigger_alert = False
    template_name = None

    def get_success_url(self):
        return self.success_url or reverse_lazy(f"{self.model._meta.model_name}_list")

    def get_template_names(self):
        return [self.template_name or f"crm/{self.model._meta.model_name}_form.html"]

    def handle_htmx_redirect(self):
        if self.request.headers.get("HX-Request") == "true":
            return HttpResponse(status=200, headers={"HX-Redirect": self.get_success_url()})
        return None

    def handle_form_exception(self, exc):
        return self.alert(self.request, str(exc), AlertStatus.INTERNAL_ERROR, False)

    def handle_form_invalid(self, form):
        return self.alert(self.request, get_first_field_error(form), AlertStatus.BAD_REQUEST, reswap=False)

class CRMCreateView(CRMBaseView, AlertMixin, CreateView):
    def form_valid(self, form):
        try:
            self.object = form.save()
            if self.trigger_alert:
                return self.alert(self.request, "Successfully created!", AlertStatus.SUCCESS, False)
            htmx_redirect = self.handle_htmx_redirect()
            if htmx_redirect:
                return htmx_redirect
            return super().form_valid(form)
        except Exception as e:
            return self.handle_form_exception(e)

    def form_invalid(self, form):
        return self.handle_form_invalid(form)

class CRMUpdateView(CRMBaseView, AlertMixin, UpdateView):
    trigger_alert = True

    def form_valid(self, form):
        try:
            self.object = form.save()
            if self.trigger_alert:
                return self.alert(self.request, "Successfully updated!", AlertStatus.SUCCESS, False)
            htmx_redirect = self.handle_htmx_redirect()
            if htmx_redirect:
                return htmx_redirect
            return super().form_valid(form)
        except Exception as e:
            return self.handle_form_exception(e)

    def form_invalid(self, form):
        return self.handle_form_invalid(form)

class CRMDeleteView(CRMBaseView, DeleteView):
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()

        htmx_redirect = self.handle_htmx_redirect()
        if htmx_redirect:
            return htmx_redirect

        return redirect(self.get_success_url())

class CRMListView(CRMBaseView, ListView):
    paginate_by = 10
    filter_form_class = None
    create_form_class = None

    def get_queryset(self):
        queryset = self.model.objects.all()
        if self.filter_form_class:
            self.filter_form = self.filter_form_class(self.request.GET)
            if self.filter_form.is_valid():
                model_fields = {f.name for f in self.model._meta.get_fields()}
                filters = {
                    k: v for k, v in self.filter_form.cleaned_data.items()
                    if k in model_fields and v not in [None, '']
                }
                queryset = queryset.filter(**filters)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("js_files", [])
        context["js_files"] += ["js/pagination.js", "js/filter.js"]

        if self.filter_form_class:
            context["filter_form"] = getattr(self, "filter_form", self.filter_form_class())
        if self.create_form_class:
            context["create_form"] = self.create_form_class()

        return context

class CRMDetailView(CRMBaseView, DetailView):
    form_class = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form_class:
            context["form"] = self.form_class(instance=self.object)
        return context

class CRMDetailTemplateView(CRMDetailView):
    template_name = "crm/base_detail.html"
    update_url = None

    def get_update_url(self):
        if self.update_url:
            return self.update_url
        model_name = self.model._meta.model_name
        return f"{model_name}_update"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update_url"] = self.get_update_url()
        return context

class CRMCreateTemplateView(CRMCreateView):
    template_name = "crm/base_create.html"
    create_url = None

    def get_create_url(self):
        if self.create_url:
            return self.create_url
        model_name = self.model._meta.model_name
        return f"{model_name}_create"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["create_url"] = self.get_create_url()
        return context

class CRMTableView(CRMListView):
    template_name = "crm/base_table.html"
    context_object_name = "table"
    table_class = None
    create_url = None
    show_add_button = True

    def get_create_url(self):
        return self.create_url or f"{self.model._meta.model_name}_create"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.table_class:
            table = self.table_class(self.object_list)
            table.request = self.request
            context["table"] = table
        context["create_url"] = self.get_create_url()
        context["show_add_button"] = self.show_add_button
        return context

class LeadListView(CRMListView):
    model = Lead
    template_name = 'crm/lead_list.html'
    filter_form_class = LeadFilterForm
    context_object_name = 'leads'

    def get_queryset(self):
        queryset = super().get_queryset()
        
        search = self.request.GET.get('search')
        
        if search:
            search_query = SearchQuery(search, search_type='plain')

            queryset = queryset.annotate(
                rank=SearchRank(F('search_vector'), search_query)
            ).filter(search_vector=search_query)

            queryset = queryset.order_by('-rank')

        return queryset

class LeadUpdateView(CRMUpdateView):
    model = Lead
    form_class = LeadForm

class LeadDetailView(CRMDetailView):
    model = Lead
    template_name = 'crm/lead_detail.html'
    form_class = LeadForm
    context_object_name = 'lead'

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

        context['quote_table'] = QuoteTable(data=self.object.quotes.all())

        initial={ 'lead': self.object }
        context['quote_form'] = QuoteForm(initial)
        context['quick_quote_form'] = QuickQuoteForm(initial)

        return context

class LeadMarketingUpdateView(CRMUpdateView):
    model = LeadMarketing
    form_class = LeadMarketingForm

class LeadArchiveView(CRMUpdateView):
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

class CocktailUpdateView(CRMUpdateView):
    model = Cocktail
    form_class = CocktailForm

class CocktailDetailView(CRMDetailTemplateView):
    template_name = 'crm/cocktail_detail.html'
    context_object_name = 'cocktail'
    model = Cocktail
    form_class = CocktailForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        initial = { 'cocktail': self.object }
        
        context.update({
            'cocktail_ingredients_form': CocktailIngredientForm(initial=initial),
            'cocktail_ingredients_table': CocktailIngredientTable(data=CocktailIngredient.objects.filter(cocktail=self.object), request=self.request),
        })

        return context

class CocktailDeleteView(CRMDeleteView):
    model = Cocktail
    form_class = CocktailForm
    
class ServiceListView(CRMTableView):
    model = Service
    table_class = ServiceTable

class ServiceCreateView(CRMCreateTemplateView):
    model = Service
    form_class = ServiceForm

class ServiceUpdateView(CRMUpdateView):
    model = Service
    form_class = ServiceForm

class ServiceDetailView(CRMDetailTemplateView):
    model = Service
    form_class = ServiceForm

class ServiceDeleteView(CRMDeleteView):
    model = Service
    form_class = ServiceForm
    
class UserListView(CRMTableView):
    model = User
    table_class = UserTable

class UserCreateView(CRMCreateTemplateView):
    model = User
    form_class = UserForm

class UserUpdateView(CRMUpdateView):
    model = User
    form_class = UserForm

class UserDetailView(CRMDetailTemplateView):
    model = User
    form_class = UserForm

class UserDeleteView(CRMDeleteView):
    model = User
    form_class = UserForm
    
class EventListView(CRMTableView):
    model = Event
    table_class = EventTable

class EventCreateView(CRMCreateTemplateView):
    model = Event
    form_class = EventForm

class EventUpdateView(CRMUpdateView):
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
            'create_shopping_list_form': EventShoppingListForm(initial=initial),
            'event_shopping_list': EventShoppingList.objects.filter(event=self.object).first()
        })

        return context

class EventDeleteView(CRMDeleteView):
    model = Event
    form_class = EventForm

class MessageListView(CRMTableView):
    model = Message
    table_class = MessageTable
    show_add_button = False

class MessageDetailView(CRMDetailTemplateView):
    model = Message
    form_class = MessageForm

class MessageUpdateView(CRMUpdateView):
    model = Message
    form_class = MessageForm

class PhoneCallListView(CRMTableView):
    model = PhoneCall
    table_class = PhoneCallTable
    show_add_button = False

class PhoneCallDetailView(CRMDetailTemplateView):
    model = PhoneCall
    form_class = PhoneCallForm

class PhoneCallUpdateView(CRMUpdateView):
    model = PhoneCall
    form_class = PhoneCallForm

class HTTPLogListView(CRMListView):
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

class CallTrackingNumberUpdateView(CRMUpdateView):
    model = CallTrackingNumber
    form_class = CallTrackingNumberForm

class CallTrackingNumberDetailView(CRMDetailTemplateView):
    model = CallTrackingNumber
    form_class = CallTrackingNumberForm

class CallTrackingNumberDeleteView(CRMDeleteView):
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

class LeadNoteCreateView(CRMCreateView):
    model = LeadNote
    form_class = LeadNoteForm

class LeadNoteUpdateView(CRMUpdateView):
    model = LeadNote
    form_class = LeadNoteForm

class LeadNoteDeleteView(CRMDeleteView):
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

class EventCocktailCreateView(CRMCreateTemplateView):
    model = EventCocktail
    form_class = EventCocktailForm

    def form_valid(self, form):
        try:
            self.object = form.save()

            event = self.object.event
            qs = EventCocktail.objects.filter(event=event)
            table = EventCocktailTable(data=qs, request=self.request)

            return HttpResponse(table.render())
        except Exception as e:
            return self.alert(request=self.request, message=str(e), status=AlertStatus.INTERNAL_ERROR, reswap=True)

    def form_invalid(self, form):
        return self.alert(request=self.request, message=get_first_field_error(form), status=AlertStatus.BAD_REQUEST, reswap=True)

class EventCocktailDeleteView(AlertMixin, CRMDeleteView):
    model = EventCocktail
    form_class = EventCocktailForm

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            self.object.delete()
            qs = EventCocktail.objects.filter(event=self.object.event)
            table = EventCocktailTable(data=qs, request=self.request)

            return HttpResponse(table.render())
        except Exception as e:
            return self.alert(request=self.request, message=str(e), status=AlertStatus.INTERNAL_ERROR, reswap=True)

class EventStaffCreateView(CRMCreateTemplateView):
    model = EventStaff
    form_class = EventStaffForm

    def form_valid(self, form):
        try:
            self.object = form.save()

            event = self.object.event
            qs = EventStaff.objects.filter(event=event)
            table = EventStaffTable(data=qs, request=self.request)

            return HttpResponse(table.render())
        except BaseException as e:
            return self.alert(request=self.request, message=get_first_field_error(form), status=AlertStatus.INTERNAL_ERROR, reswap=True)

class EventStaffDeleteView(AlertMixin, CRMDeleteView):
    model = EventStaff
    form_class = EventStaffForm

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            self.object.delete()
            qs = EventStaff.objects.filter(event=self.object.event)
            table = EventStaffTable(data=qs, request=self.request)

            return HttpResponse(table.render())
        except Exception as e:
            return self.alert(request=self.request, message=str(e), status=AlertStatus.INTERNAL_ERROR, reswap=True)
    
class CocktailIngredientCreateView(CRMCreateTemplateView):
    model = CocktailIngredient
    form_class = CocktailIngredientForm

    def form_valid(self, form):
        try:
            self.object = form.save()

            cocktail = self.object.cocktail
            qs = CocktailIngredient.objects.filter(cocktail=cocktail)
            table = CocktailIngredientTable(data=qs, request=self.request)

            return HttpResponse(table.render())
        except Exception as e:
            return self.alert(request=self.request, message=get_first_field_error(form), status=AlertStatus.INTERNAL_ERROR, reswap=True)

class CocktailIngredientDeleteView(AlertMixin, CRMDeleteView):
    model = CocktailIngredient
    form_class = CocktailIngredientForm

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            self.object.delete()
            qs = CocktailIngredient.objects.filter(cocktail=self.object.cocktail)
            table = CocktailIngredientTable(data=qs, request=self.request)

            return HttpResponse(table.render())
        except Exception as e:
            return self.alert(request=self.request, message=str(e), status=AlertStatus.INTERNAL_ERROR, reswap=True)

class IngredientListView(CRMTableView):
    model = Ingredient
    table_class = IngredientTable

class IngredientCreateView(CRMCreateTemplateView):
    model = Ingredient
    form_class = IngredientForm

class IngredientUpdateView(CRMUpdateView):
    model = Ingredient
    form_class = IngredientForm

class IngredientDetailView(CRMDetailTemplateView):
    model = Ingredient
    form_class = IngredientForm

class IngredientDeleteView(CRMDeleteView):
    model = Ingredient
    form_class = IngredientForm

class CreateShoppingListView(CRMCreateView):
    model = EventShoppingList
    form_class = EventShoppingListForm

    def get_object(self, queryset=None):
        event_id = self.request.POST.get('event')

        if not event_id:
            return None

        event = Event.objects.filter(pk=event_id).first()

        if not event:
            return None

        return getattr(event, 'shopping_list', None)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        instance = self.get_object()
        if instance:
            kwargs['instance'] = instance
        return kwargs

    def form_valid(self, form):
        try:
            event_shopping_list = form.save()

            # Clear any previous entries
            event_shopping_list.entries.all().delete()

            event = event_shopping_list.event

            if not event.guests or not event.start_time or not event.end_time:
                raise ValidationError('Fill out event details before creating a shopping list.')

            duration = event.end_time - event.start_time
            hours = duration.total_seconds() / 3600
            expected_consumed_cocktails = event.guests * hours

            event_cocktails = EventCocktail.objects.filter(event=event)
            if not event_cocktails.exists():
                raise ValidationError('There must be at least one cocktail before creating a shopping list.')

            expected_consumption_per_cocktail = expected_consumed_cocktails / event_cocktails.count()

            # Cache all StoreItems for quick lookup
            store_items_by_name = {
                item.name: item for item in StoreItem.objects.all()
            }

            # Cache new entries to avoid duplicate creations
            new_entries_by_store_item_id = {}

            for event_cocktail in event_cocktails:
                cocktail_ingredients = CocktailIngredient.objects.filter(cocktail=event_cocktail.cocktail)

                if not cocktail_ingredients.exists():
                    raise ValidationError(f'Assign cocktail ingredients to {event_cocktail.cocktail}.')

                for ingredient in cocktail_ingredients:
                    item_name = ingredient.ingredient.name
                    store_item = store_items_by_name.get(item_name)

                    if not store_item:
                        raise ValidationError(f'Invalid store item for ingredient: {item_name}')

                    qty = expected_consumption_per_cocktail * ingredient.amount

                    suggested_quantity = convert_to_item_quantity(ingredient, store_item, qty)

                    existing_entry = new_entries_by_store_item_id.get(store_item.pk)

                    if existing_entry:
                        existing_entry.quantity += suggested_quantity
                    else:
                        new_entries_by_store_item_id[store_item.pk] = EventShoppingListEntry(
                            store_item=store_item,
                            quantity=suggested_quantity,
                            unit=ingredient.unit,
                            event_shopping_list=event_shopping_list,
                        )

            # Save all entries at once
            EventShoppingListEntry.objects.bulk_create(new_entries_by_store_item_id.values())

            return HttpResponse()

        except Exception as e:
            return self.alert(
                request=self.request,
                message=str(e),
                status=AlertStatus.INTERNAL_ERROR
            )

class EventShoppingListExternalDetailView(DetailView):
    model = EventShoppingList
    template_name = 'crm/shopping_list_detail.html'
    context_object_name = 'event_shopping_list'

    def get_object(self, queryset=None):
        external_id = self.kwargs.get("external_id")
        return get_object_or_404(EventShoppingList, external_id=external_id)

class StoreItemListView(CRMTableView):
    model = StoreItem
    table_class = StoreItemTable

class StoreItemCreateView(CRMCreateTemplateView):
    model = StoreItem
    form_class = StoreItemForm

class StoreItemUpdateView(CRMUpdateView):
    model = StoreItem
    form_class = StoreItemForm

class StoreItemDetailView(CRMDetailTemplateView):
    model = StoreItem
    form_class = StoreItemForm

class StoreItemDeleteView(CRMDeleteView):
    model = StoreItem
    form_class = StoreItemForm

class QuoteCreateView(CRMCreateTemplateView):
    model = Quote
    form_class = QuoteForm
    trigger_alert = False

    def form_valid(self, form):
        try:
            self.object = form.save()

            qs = Quote.objects.filter(lead=self.object.lead)
            table = QuoteTable(data=qs, request=self.request)

            return HttpResponse(table.render())
        except Exception as e:
            print(f'ERROR ADDING QUOTE: {e}')
            return self.alert(request=self.request, message='Error while creating quote.', status=AlertStatus.INTERNAL_ERROR, reswap=True)

class QuoteUpdateView(CRMUpdateView):
    model = Quote
    form_class = QuoteForm
    trigger_alert = False

    def get_success_url(self):
        return reverse('quote_detail', kwargs={'pk': self.object.pk})

class QuoteDetailView(CRMDetailTemplateView):
    template_name = 'crm/quote_detail.html'
    model = Quote
    form_class = QuoteForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        quote = self.object
        context['quote_service_table'] = QuoteServiceTable(data=quote.quote_services.all(), request=self.request)
        context['quote_service_form'] = QuoteServiceForm(initial={ 'quote': quote })
        context['quote_send_form'] = QuoteSendForm(initial={ 'quote': quote })

        return context

class QuoteDeleteView(CRMDeleteView):
    model = Quote
    form_class = QuoteForm

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            self.object.delete()
            qs = Quote.objects.filter(lead=self.object.lead)
            table = QuoteTable(data=qs, request=self.request)

            return HttpResponse(table.render())
        except Exception as e:
            return self.alert(request=self.request, message=str(e), status=AlertStatus.INTERNAL_ERROR, reswap=True)

class QuoteServiceCreateView(CRMCreateTemplateView):
    model = QuoteService
    form_class = QuoteServiceForm

    def form_valid(self, form):
        try:
            self.object = form.save()

            qs = QuoteService.objects.filter(quote=self.object.quote)
            table = QuoteServiceTable(data=qs, request=self.request)

            return HttpResponse(table.render())
        except Exception as e:
            return self.alert(request=self.request, message=str(e), status=AlertStatus.INTERNAL_ERROR, reswap=True)

class QuoteServiceDeleteView(AlertMixin, CRMDeleteView):
    model = QuoteService
    form_class = QuoteServiceForm

    def post(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            self.object.delete()
            qs = QuoteService.objects.filter(quote=self.object.quote)
            table = QuoteServiceTable(data=qs, request=self.request)

            return HttpResponse(table.render())
        except Exception as e:
            return self.alert(request=self.request, message=str(e), status=AlertStatus.INTERNAL_ERROR, reswap=True)

class QuotePresetListView(CRMTableView):
    model = QuotePreset
    table_class = QuotePresetTable

class QuotePresetCreateView(CRMCreateTemplateView):
    model = QuotePreset
    form_class = QuotePresetForm

class QuotePresetUpdateView(CRMUpdateView):
    model = QuotePreset
    form_class = QuotePresetForm

class QuotePresetDetailView(CRMDetailTemplateView):
    model = QuotePreset
    form_class = QuotePresetForm

class QuotePresetDeleteView(CRMDeleteView):
    model = QuotePreset
    form_class = QuotePresetForm

class QuickQuoteCreateView(CRMCreateTemplateView):
    model = Quote
    form_class = QuickQuoteForm
    trigger_alert = False

    def form_valid(self, form):
        try:
            form.save()
            lead = form.cleaned_data.get('lead')

            if not lead:
                raise ValueError('Lead not found.')

            qs = Quote.objects.filter(lead=lead)
            table = QuoteTable(data=qs, request=self.request)

            return HttpResponse(table.render())
        except Exception as e:
            return self.alert(request=self.request, message='Error while creating quick quote.', status=AlertStatus.INTERNAL_ERROR)

class ExternalQuoteView(CRMContextMixin, DetailView):
    template_name = 'crm/external_quote_view.html'
    model = Quote
    context_object_name = 'quote'

    def get_object(self, queryset=None):
        external_id = self.kwargs.get('external_id')
        return get_object_or_404(Quote, external_id=external_id)

class QuoteSendView(CRMBaseView, AlertMixin, FormView):
    model = Quote
    form_class = QuoteSendForm

    def post(self, request, *args, **kwargs):
        try:
            form = self.form_class(request.POST)
            if form.is_valid():
                quote = form.cleaned_data.get('quote')
                if not quote:
                    return self.alert(request=self.request, message="Quote cannot be none!", status=AlertStatus.BAD_REQUEST, reswap=True)
                text_content = settings.COMPANY_NAME + ' QUOTE:\n' + settings.ROOT_DOMAIN + reverse('external_quote_view', kwargs={ 'external_id': quote.external_id })
                message = Message(
                        text=format_text_message(text_content),
                        text_from=settings.COMPANY_PHONE_NUMBER,
                        text_to=quote.lead.phone_number,
                        is_inbound=False,
                        status='sent',
                        is_read=True,
                    )
                resp = messaging_service.send_text_message(message=message)
                message.external_id = resp.sid
                message.status = resp.status
                message.save()

                quote.lead.change_lead_status(LeadStatusEnum.INVOICE_SENT)
                return self.alert(request=self.request, message="Quote sent!", status=AlertStatus.SUCCESS, reswap=True)
            else:
                return self.alert(request=self.request, message="Form invalid.", status=AlertStatus.BAD_REQUEST, reswap=True)
        except Exception as e:
            return self.alert(request=self.request, message=str(e), status=AlertStatus.INTERNAL_ERROR, reswap=True)
