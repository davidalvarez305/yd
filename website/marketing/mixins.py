from datetime import datetime
import json
import uuid
import random

from django.http import HttpRequest
from django.utils.timezone import now, timedelta
from django.utils.dateparse import parse_datetime

from core.models import LeadMarketing, CallTrackingNumber, CallTracking, Visit
from core.logger import logger
from website import settings

from .utils import MarketingHelper, is_paid_traffic
from .enums import MarketingParams

tracking_number = MarketingParams.CallTrackingNumberSessionValue.value

class CallTrackingMixin:
    def dispatch(self, request: HttpRequest, *args, **kwargs):
        if is_paid_traffic(request=request) and not request.user.is_authenticated:
            self.clean_up_expired_session(request)

            if not request.session.get(tracking_number):
                self.track_call(request)

        return super().dispatch(request, *args, **kwargs)

    def track_call(self, request: HttpRequest):
        try:
            tracking_numbers = list(CallTrackingNumber.objects.filter(date_expires__gt=now()))

            if tracking_numbers:
                call_tracking_number = random.choice(tracking_numbers)
            else:
                call_tracking_number = CallTrackingNumber.objects.get(phone_number=settings.DEFAULT_TRACKING_NUMBER)

            data = {
                'phone_number': call_tracking_number.phone_number,
                'timestamp': now().isoformat(),
            }

            request.session['tracking_number'] = data

            metadata = MarketingHelper(request)
            
            call_tracking = CallTracking(
                call_tracking_number=call_tracking_number,
                metadata=json.dumps(metadata.to_dict()),
                external_id=request.session.get('external_id')
            )
            call_tracking.save()
        except Exception as e:
            logger.error(e, exc_info=True)
            raise Exception('Error during tracking call.')

    def clean_up_expired_session(self, request):
        data = request.session.get(tracking_number, None)
        if not data:
            return

        session_time = data.get('timestamp', None)

        if not session_time:
            return
        
        if isinstance(session_time, str):
            timestamp = parse_datetime(session_time)
        elif isinstance(session_time, datetime):
            timestamp = session_time
        else:
            return

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

            lead_marketing = LeadMarketing.objects.filter(external_id=external_id).first()
            visit = Visit.objects.create(
                external_id=external_id,
                referrer=referrer,
                url=url,
                lead_marketing=lead_marketing,
            )

            request.session['visit_id'] = visit.visit_id

        return super().dispatch(request, *args, **kwargs)