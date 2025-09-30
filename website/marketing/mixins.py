import uuid
import random

from django.conf import settings
from core.models import LandingPage, LeadMarketing, SessionMapping, Visit
from .utils import MarketingHelper, is_paid_traffic
    
class UserTrackingMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            if not request.session.session_key:
                request.session.create()

            external_id = request.session.get("external_id")
            if not external_id:
                external_id = str(uuid.uuid4())

            mapping_exists = SessionMapping.objects.filter(external_id=external_id).exists()

            if not mapping_exists:
                self._init_user_tracking(request, external_id)

        return super().dispatch(request, *args, **kwargs)

    def _init_user_tracking(self, request, external_id: str):
        helper = MarketingHelper(request=request)

        request.session["external_id"] = external_id
        request.session["ip"] = helper.ip
        request.session["user_agent"] = helper.user_agent

        SessionMapping.objects.create(
            external_id=external_id,
            session_key=request.session.session_key,
        )

        request.external_id_cookie = external_id

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        external_id = getattr(self.request, 'external_id_cookie', None)
        if external_id:
            response.set_cookie(
                settings.TRACKING_COOKIE_NAME,
                external_id,
                max_age=settings.SESSION_COOKIE_AGE,
                secure=True,
                httponly=False,
                samesite="Lax",
            )
        return response

class VisitTrackingMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            referrer = request.META.get('HTTP_REFERER')
            external_id = request.session.get('external_id')

            lead_marketing = LeadMarketing.objects.filter(external_id=external_id).first()

            visit = Visit(
                external_id=external_id,
                referrer=referrer,
                url=request.build_absolute_uri(),
                lead_marketing=lead_marketing,
            )

            if not request.GET.get('test'):
                lp = request.session.get('landing_page_id')
                if lp:
                    visit.landing_page = LandingPage.objects.filter(pk=lp).first()

            visit.save()

            request.session['visit_id'] = visit.visit_id

        return super().dispatch(request, *args, **kwargs)
    
class LandingPageMixin:
    def dispatch(self, request, *args, **kwargs):
        if is_paid_traffic(request=request):
            landing_page = self.get_random_landing_page()
            if landing_page:
                request.session["landing_page_id"] = landing_page.pk

        return super().dispatch(request, *args, **kwargs)

    def get_random_landing_page(self) -> LandingPage | None:
        pages = list(LandingPage.objects.filter(is_active=True))
        if not pages:
            return None
        return random.choice(pages)