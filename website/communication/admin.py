from django.contrib import admin
from .models import Message, MessageMedia

admin.site.register(Message)
admin.site.register(MessageMedia)