from django.utils import timezone
from django.shortcuts import redirect
from django.http import HttpResponseServerError
from .models import CallTracking, CallTrackingNumber, LandingPage
import random
from .enums import MarketingParams, ConversionServiceType

class CallTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        urls = LandingPage.objects.values_list('url', flat=True)

        self.clean_up_expired_session(request)

        if not urls:
            return HttpResponseServerError("No landing page URLs found")

        if request.path in urls:
            self.track_call(request)

        response = self.get_response(request)
        return response

    def track_call(self, request):
        # Step 1: Check for gclid or fbclid in the URL using Enum
        gclid = request.GET.get(MarketingParams.GoogleURLClickID.value, None)
        fbclid = request.GET.get(MarketingParams.FacebookURLClickID.value, None)

        # Step 2: Determine the platform_id
        platform_id: ConversionServiceType | None = None
        if gclid:
            platform_id = CallTrackingNumber.GOOGLE
        elif fbclid:
            platform_id = CallTrackingNumber.FACEBOOK

        # Step 3: Only proceed if a platform_id is found
        if platform_id is not None:
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

                # Step 6: Store value in session
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