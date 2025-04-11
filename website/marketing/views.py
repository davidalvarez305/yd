from .models import ConversionLog, CallTrackingNumber
from .forms import ConversionLogFilterForm, CallTrackingFilterForm, CallTrackingNumberForm
from website.crm.views import CRMBaseListView, CRMBaseDetailView, CRMBaseDeleteView, CRMBaseCreateView, CRMBaseUpdateView

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