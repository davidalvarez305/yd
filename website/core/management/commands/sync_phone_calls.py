from django.core.management.base import BaseCommand
from core.models import PhoneCall, User

class Command(BaseCommand):
    help = 'Delete phone calls where call_to is in excluded numbers.'

    def handle(self, *args, **options):
        EXCLUDED_NUMBERS = []

        superadmins = User.objects.filter(is_superuser=True)
        for user in superadmins:
            if user.forward_phone_number:
                EXCLUDED_NUMBERS.append(user.forward_phone_number.strip())

        deleted_count, _ = PhoneCall.objects.filter(
            call_to__in=EXCLUDED_NUMBERS
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted_count} phone calls.")
        )