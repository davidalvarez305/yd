from django.http import HttpResponse
from django.views.generic.edit import UpdateView

from .models import Visit
from .forms import HTTPLogFilterForm, CallTrackingFilterForm, CallTrackingNumberForm, VisitForm, VisitFilterForm
from crm.views import CRMBaseListView, CRMBaseDetailView, CRMBaseDeleteView, CRMBaseCreateView, CRMBaseUpdateView
from core.models import HTTPLog, CallTrackingNumber

class HTTPLogListView(CRMBaseListView):
    model = HTTPLog
    context_object_name = "logs"
    filter_form_class = HTTPLogFilterForm

class CallTrackingNumberListView(CRMBaseListView):
    model = CallTrackingNumber
    filter_form_class = CallTrackingFilterForm

class CallTrackingNumberCreateView(CRMBaseCreateView):
    model = CallTrackingNumber
    form_class = CallTrackingNumberForm

class CallTrackingNumberUpdateView(CRMBaseUpdateView):
    model = CallTrackingNumber
    form_class = CallTrackingNumberForm

class CallTrackingNumberDetailView(CRMBaseDetailView):
    model = CallTrackingNumber

class CallTrackingNumberDeleteView(CRMBaseDeleteView):
    model = CallTrackingNumber

class VisitListView(CRMBaseListView):
    model = Visit
    filter_form_class = VisitFilterForm
    context_object_name = "visits"

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.order_by('-date_created')

class VisitUpdateView(UpdateView):
    form_class = VisitForm
    model = Visit
    http_method_names = ['post']
    
    def form_valid(self, form):
        form.save()
        return HttpResponse("Updated")