from django.utils.timezone import now
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404

from website import settings
from website.core.views import BaseView

class CRMBaseView(LoginRequiredMixin, BaseView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Additional CRM-specific context
        context.update({
            "assumed_base_hours_for_per_person_pricing": settings.ASSUMED_BASE_HOURS,
        })

        # Fetch unread messages count
        context["unread_messages"] = Message.objects.filter(is_read=False).count()

        # Get user's phone number
        user = get_object_or_404(User, user=self.request.user)
        context["crm_user_phone_number"] = user.phone_number

        return context

class IndexView(CRMBaseView):
    template_name = "index.html"