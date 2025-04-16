from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.db import connection
from django.core.paginator import Paginator

from website import settings
from core.views import BaseView
from communication.models import Message
from core.models import User, Lead
from crm.forms import LeadForm, LeadFilterForm
from crm.models import Lead

class CRMBaseView(LoginRequiredMixin, BaseView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Additional CRM-specific context
        context.update({
            "assumed_base_hours_for_per_person_pricing": settings.ASSUMED_BASE_HOURS,
        })

        # Fetch unread messages count
        context["unread_messages"] = Message.objects.filter(is_read=False).count()

        """ # Get user's phone number
        user = get_object_or_404(User, user=self.request.user)
        print(user)
        context["crm_user_phone_number"] = user.phone_number """

        # Inject the JavaScript files into the context for the view
        context['js_files'] = [
            'js/nav.js',
            'js/main.js'
        ]

        return context

class CRMBaseListView(CRMBaseView, ListView):
    """
    A base list view class for CRM views. Automatically injects filters based on form.
    This class can be extended for more complex filtering logic as needed.
    """
    filter_form_class = None
    paginate_by = 10
    context_object_name = None  # Default is None, which will use a pluralized model name

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return self.render_to_response(context)

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

        # Set the default context object name to the plural version of the model name
        if not self.context_object_name:
            self.context_object_name = f"{self.model._meta.model_name}s"  # Pluralize model name

        # Add the object list to context with the context name (either the default or custom)
        context[self.context_object_name] = self.get_queryset()

        # Inject the JavaScript files into the context for the view
        context['js_files'] += [
            'js/pagination.js',
            'js/filter.js',
            'js/modal.js'
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

class LeadListView(CRMBaseListView):
    model = Lead
    filter_form_class = LeadFilterForm

    def get_queryset(self):
        params = self.request.GET
        page = int(params.get('page', 1))
        limit = self.paginate_by
        offset = (page - 1) * limit

        search = params.get('search')
        lead_status_id = params.get('lead_status_id')
        lead_interest_id = params.get('lead_interest_id')
        next_action_id = params.get('next_action_id')

        with connection.cursor() as cursor:
            query = """
            WITH combined_communications AS (
                SELECT text_from AS phone_number, date_created FROM message
                UNION ALL
                SELECT text_to AS phone_number, date_created FROM message
                UNION ALL
                SELECT call_from AS phone_number, date_created FROM phone_call
                UNION ALL
                SELECT call_to AS phone_number, date_created FROM phone_call
            ),
            latest_communication AS (
                SELECT DISTINCT ON (phone_number) phone_number, date_created
                FROM combined_communications
                ORDER BY phone_number, date_created DESC
            ),
            latest_lead_next_action AS (
                SELECT DISTINCT ON (lead_id) lead_id, action_date, next_action_id
                FROM lead_next_action
                ORDER BY lead_id, action_date DESC
            )
            SELECT 
                l.lead_id, 
                l.full_name, 
                l.phone_number, 
                l.created_at, 
                lm.language, 
                li.interest, 
                ls.status, 
                COALESCE(nsa.action, na.action) AS next_action,
                lna.action_date, 
                lc.date_created AS last_contact_date,
                MAX(q.event_date) as event_date,
                COUNT(*) OVER() AS total_rows
            FROM lead AS l
            JOIN lead_marketing AS lm ON lm.lead_id = l.lead_id
            LEFT JOIN lead_interest AS li ON li.lead_interest_id = l.lead_interest_id
            LEFT JOIN lead_status AS ls ON ls.lead_status_id = l.lead_status_id
            LEFT JOIN next_action AS na ON na.next_action_id = l.next_action_id
            LEFT JOIN latest_lead_next_action AS lna ON lna.lead_id = l.lead_id
            LEFT JOIN next_action AS nsa ON nsa.next_action_id = lna.next_action_id
            LEFT JOIN latest_communication AS lc ON lc.phone_number = l.phone_number
            LEFT JOIN quote as q ON q.lead_id = l.lead_id
            WHERE 
                (
                    %s IS NOT NULL 
                    AND (
                        l.search_vector @@ plainto_tsquery('english', %s)
                        OR l.full_name ILIKE '%%' || %s || '%%'
                        OR l.phone_number ILIKE '%%' || %s || '%%'
                        OR EXISTS (
                            SELECT 1 FROM lead_note ln 
                            WHERE ln.lead_id = l.lead_id 
                            AND ln.note ILIKE '%%' || %s || '%%'
                        )
                    )
                )
                OR 
                (
                    %s IS NULL 
                    AND (
                        (%s IS NOT NULL AND ls.lead_status_id = %s) 
                        OR 
                        (%s IS NULL AND (ls.lead_status_id IS DISTINCT FROM %s OR ls.lead_status_id IS NULL))
                    )
                    AND 
                    (
                        (%s IS NOT NULL AND li.lead_interest_id = %s) 
                        OR 
                        (%s IS NULL AND (li.lead_interest_id IS DISTINCT FROM %s OR li.lead_interest_id IS NULL))
                    )
                    AND 
                    (%s IS NULL OR na.next_action_id = %s)
                )
            GROUP BY 
                l.lead_id, 
                l.full_name, 
                l.phone_number, 
                l.created_at, 
                lm.language, 
                li.interest, 
                ls.status, 
                nsa.action, 
                na.action, 
                lna.action_date, 
                lc.date_created
            ORDER BY l.created_at DESC
            LIMIT %s OFFSET %s;
            """

            cursor.execute(query, [
                search, search, search, search, search,
                search,
                lead_status_id, lead_status_id, lead_status_id, ARCHIVED_LEAD_STATUS_ID,
                lead_interest_id, lead_interest_id, lead_interest_id, NO_INTEREST_LEAD_INTEREST_ID,
                next_action_id, next_action_id,
                limit, offset
            ])

            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        total_rows = results[0]["total_rows"] if results else 0

        paginator = Paginator(results, limit)
        self.extra_context = {"total_rows": total_rows}
        return paginator.page(page)

class LeadUpdateView(CRMBaseUpdateView):
    form_class = LeadForm

class LeadDetailView(CRMBaseDetailView):
    model = Lead

class LeadDeleteView(CRMBaseDeleteView):
    model = Lead