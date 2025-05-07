import uuid
import random

from django.utils import timezone

from core.models import LeadMarketing, LandingPage, CallTrackingNumber, CallTracking

from .models import Visit
from .enums import MarketingParams

class CallTrackingMixin:
    def dispatch(self, request, *args, **kwargs):
        urls = LandingPage.objects.values_list('url', flat=True)

        self.clean_up_expired_session(request)

        if urls and request.path in urls:
            self.track_call(request)

        return super().dispatch(request, *args, **kwargs)

    def track_call(self, request):
        # Step 1: Check for gclid or fbclid in the URL using Enum
        gclid = request.GET.get(MarketingParams.GoogleURLClickID.value, None)
        fbclid = request.GET.get(MarketingParams.FacebookURLClickID.value, None)

        # Step 2: Determine the platform_id
        platform_id = None
        if gclid:
            platform_id = CallTrackingNumber.GOOGLE
        elif fbclid:
            platform_id = CallTrackingNumber.FACEBOOK

        # Step 3: Only proceed if a platform_id is found
        if platform_id is not None:
            return

        client_id = None
        if gclid:
            client_id = request.COOKIES.get(MarketingParams.GoogleAnalyticsCookieClientID.value, None)

        if not client_id:
            client_id = request.COOKIES.get(MarketingParams.FacebookCookieClientID.value, None)

        # Step 4: Assign the click_id
        click_id = fbclid if fbclid else gclid

        # Step 5: If client_id and click_id are available, save the data
        if client_id and click_id:
            phone_number = random.choice(CallTrackingNumber.objects.filter(platform_id=platform_id))

            # Step 6: Store the value in session
            request.session[MarketingParams.CallTrackingNumberSessionValue.value] = phone_number.call_tracking_number

            # Step 7: Create a new CallTracking record
            call_tracking = CallTracking(
                call_tracking_number=phone_number,
                date_assigned=timezone.now(),
                date_expires=timezone.now() + timezone.timedelta(minutes=10),
                client_id=client_id,
                click_id=click_id
            )
            call_tracking.save()

    def clean_up_expired_session(self, request):
        session_data = request.session.get(MarketingParams.CallTrackingNumberSessionValue.value, None)
        if session_data:
            timestamp = session_data.get('timestamp', None)
            if timestamp and timezone.now() - timestamp > timezone.timedelta(minutes=10):
                del request.session[MarketingParams.CallTrackingNumberSessionValue.value]

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