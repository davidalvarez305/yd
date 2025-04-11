from .models import ConversionLog, CallTrackingNumber
from .forms import ConversionLogFilterForm, CallTrackingFilterForm
from website.crm.views import CRMBaseListView, CRMBaseDetailView, CRMBaseDeleteView, CRMBaseCreateView, CRMBaseUpdateView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy

class ConversionLogListView(CRMBaseListView):
    template_name = "log_list.html"
    model = ConversionLog
    context_object_name = "logs"
    filter_form_class = ConversionLogFilterForm

class CallTrackingNumberListView(CRMBaseListView):
    template_name = "call_tracking_number_list.html"
    model = CallTrackingNumber
    context_object_name = "numbers"
    filter_form_class = CallTrackingFilterForm

class CallTrackingNumberCreateView(CRMBaseCreateView):
    model = CallTrackingNumber
    fields = ['platform_id', 'call_tracking_number', 'campaign']
    template_name = 'call_tracking_number_create.html'

class CallTrackingNumberUpdateView(CRMBaseUpdateView):
    model = CallTrackingNumber
    fields = ['platform_id', 'call_tracking_number', 'campaign']
    template_name = 'call_tracking_number_update.html'

class CallTrackingNumberDeleteView(CRMBaseDeleteView):
    model = CallTrackingNumber

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponseRedirect(self.success_url)

class CallTrackingNumberDetailView(CRMBaseDetailView):
    template_name = "call_tracking_number_detail.html"
    model = CallTrackingNumber
    context_object_name = "number"