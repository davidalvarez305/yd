import uuid
import random

from core.models import LandingPage, LeadMarketing, Visit
from .utils import is_paid_traffic

class VisitTrackingMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            referrer = request.META.get('HTTP_REFERER')
            url = request.build_absolute_uri()

            external_id = request.session.get('external_id')
            if not external_id:
                external_id = str(uuid.uuid4())
                request.session['external_id'] = external_id

            lead_marketing = LeadMarketing.objects.filter(external_id=external_id).first()
            visit = Visit.objects.create(
                external_id=external_id,
                referrer=referrer,
                url=url,
                lead_marketing=lead_marketing,
            )

            request.session['visit_id'] = visit.visit_id

        return super().dispatch(request, *args, **kwargs)
    
class LandingPageMixin:
    def dispatch(self, request, *args, **kwargs):
        if is_paid_traffic(request=request):
            visit_id = request.session.get("visit_id")

            if visit_id:
                landing_page = self.get_random_landing_page()
                if landing_page:
                    request.session["landing_page_id"] = landing_page.pk

        return super().dispatch(request, *args, **kwargs)

    def get_random_landing_page(self) -> LandingPage | None:
        pages = list(LandingPage.objects.filter(is_active=True))
        if not pages:
            return None
        return random.choice(pages)