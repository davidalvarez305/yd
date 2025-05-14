import uuid
import random

from django.utils.timezone import now, timedelta

from core.models import LeadMarketing, CallTrackingNumber, CallTracking, Visit
from website import settings

from .utils import get_marketing_params
from .enums import MarketingParams

class CallTrackingMixin:
    def dispatch(self, request, *args, **kwargs):
        self.clean_up_expired_session(request)

        self.track_call(request)

        return super().dispatch(request, *args, **kwargs)

    def track_call(self, request):
        marketing_params = get_marketing_params(request)

        click_id = marketing_params.get('click_id')
        client_id = marketing_params.get('client_id')
        platform_id = marketing_params.get('platform_id')
        external_id = request.session.get('external_id')

        if not client_id or click_id or platform_id:
            return

        phone_number = random.choice(CallTrackingNumber.objects.all())

        request.session[MarketingParams.CallTrackingNumberSessionValue.value] = {
            'call_tracking_number': phone_number.call_tracking_number,
            'timestamp': now(),
        }

        call_tracking = CallTracking(
            call_tracking_number=phone_number,
            date_assigned=now(),
            date_expires=now() + timedelta(minutes=settings.CALL_TRACKING_EXPIRATION_LIMIT),
            client_id=client_id,
            click_id=click_id,
            external_id=external_id,
        )

        call_tracking.save()

    def clean_up_expired_session(self, request):
        data = request.session.get(MarketingParams.CallTrackingNumberSessionValue.value, None)
        if not data:
            return

        timestamp = data.get('timestamp', None)

        if not timestamp:
            return
        
        time_diff = now() - timestamp
        if time_diff > timedelta(minutes=settings.CALL_TRACKING_EXPIRATION_LIMIT):
            return

        del request.session[MarketingParams.CallTrackingNumberSessionValue.value]

class VisitTrackingMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            referrer = request.META.get('HTTP_REFERER')
            url = request.build_absolute_uri()

            external_id = request.session.get('external_id')
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