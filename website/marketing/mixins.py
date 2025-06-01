import json
import uuid
import random

from django.http import HttpRequest
from django.utils.timezone import now, timedelta
from django.utils.dateparse import parse_datetime

from core.models import LeadMarketing, CallTrackingNumber, CallTracking, Visit
from website import settings

from .utils import MarketingHelper
from .enums import MarketingParams

tracking_number = MarketingParams.CallTrackingNumberSessionValue.value

class CallTrackingMixin:
    def dispatch(self, request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            self.clean_up_expired_session(request)

            # If after clean up, there still a value, wait until expiration before new assignment
            if request.session.get(tracking_number):
                return

            self.track_call(request)

        return super().dispatch(request, *args, **kwargs)

    def track_call(self, request: HttpRequest):
        tracking_numbers = CallTrackingNumber.objects.all()

        data = {
            'call_tracking_number': settings.COMPANY_PHONE_NUMBER,
            'timestamp': now().isoformat(),
        }

        if len(tracking_numbers) == 0:
            return

        phone_number = random.choice(tracking_numbers)

        data['call_tracking_number'] = phone_number.call_tracking_number
        request.session[tracking_number] = data

        metadata = MarketingHelper(request)
        
        call_tracking = CallTracking(
            call_tracking_number=phone_number,
            date_assigned=now(),
            date_expires=now() + timedelta(minutes=settings.CALL_TRACKING_EXPIRATION_LIMIT),
            metadata=json.dumps(metadata.to_dict()),
            external_id=request.session.get('external_id')
        )

        call_tracking.save()

    def clean_up_expired_session(self, request):
        data = request.session.get(tracking_number, None)
        if not data:
            return

        session_time = data.get('timestamp', None)

        if not session_time:
            return
        
        timestamp = parse_datetime(session_time)
        if not timestamp:
            return
        
        time_diff = now() - timestamp
        if time_diff > timedelta(minutes=settings.CALL_TRACKING_EXPIRATION_LIMIT):
            return

        del request.session[tracking_number]

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