from .models import ConversionLog, CallTrackingNumber, Visit
from .forms import ConversionLogFilterForm, CallTrackingFilterForm, CallTrackingNumberForm, VisitForm, VisitFilterForm
from crm.views import CRMBaseListView, CRMBaseDetailView, CRMBaseDeleteView, CRMBaseCreateView, CRMBaseUpdateView

class ConversionLogListView(CRMBaseListView):
    template_name = "log_list.html"
    model = ConversionLog
    context_object_name = "logs"
    filter_form_class = ConversionLogFilterForm

class CallTrackingNumberListView(CRMBaseListView):
    model = CallTrackingNumber
    filter_form_class = CallTrackingFilterForm

class CallTrackingNumberCreateView(CRMBaseCreateView):
    form_class = CallTrackingNumberForm

class CallTrackingNumberUpdateView(CRMBaseUpdateView):
    form_class = CallTrackingNumberForm

class CallTrackingNumberDetailView(CRMBaseDetailView):
    model = CallTrackingNumber

class CallTrackingNumberDeleteView(CRMBaseDeleteView):
    model = CallTrackingNumber

class VisitListView(CRMBaseListView):
    model = Visit
    filter_form_class = VisitFilterForm

class VisitUpdateView(CRMBaseUpdateView):
    form_class = VisitForm