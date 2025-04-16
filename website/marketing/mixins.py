import uuid
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect
from .models import Visit, LeadMarketing

class VisitTrackingMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            referrer = request.META.get('HTTP_REFERER', None)
            url = request.build_absolute_uri()

            external_id = request.session.get('external_id', None)
            if not external_id:
                external_id = str(uuid.uuid4())
                request.session['external_id'] = external_id

            visit = Visit.objects.create(
                external_id=external_id,
                referrer=referrer,
                url=url,
                lead_marketing=LeadMarketing.objects.filter(external_id=external_id).first()
            )

            request.session['visit_id'] = visit.visit_id

        return super().dispatch(request, *args, **kwargs)