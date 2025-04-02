from django.views.generic import TemplateView
from django.utils.timezone import now
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404

from website.website import settings

class CRMBaseView(LoginRequiredMixin, TemplateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            "page_title": settings.COMPANY_NAME,
            "meta_description": "Get a quote for mobile bartending services in Miami, FL.",
            "site_name": settings.SITE_NAME,
            "static_path": settings.STATIC_PATH,
            "media_path": settings.MEDIA_PATH,
            "phone_number": settings.DAVID_PHONE_NUMBER,
            "current_year": now().year,
            "company_name": settings.COMPANY_NAME,
            "assumed_base_hours_for_per_person_pricing": settings.ASSUMED_BASE_HOURS,
            "page_path": f"{settings.ROOT_DOMAIN}{self.request.path}",
        })

        # Fetch unread messages count
        context["unread_messages"] = Message.objects.filter(is_read=False).count()

        # Get user's phone number
        if self.request.user.is_authenticated:
            user = get_object_or_404(User, user=self.request.user)
            context["crm_user_phone_number"] = user.phone_number

        return context
