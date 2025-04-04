from .models import ConversionLog
from .forms import ConversionLogFilterForm
from website.crm.views import CRMBaseListView

class ConversionLogListView(CRMBaseListView):
    template_name = "log_list_view.html"
    model = ConversionLog
    context_object_name = "logs"
    filter_form_class = ConversionLogFilterForm