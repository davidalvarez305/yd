import django_filters

from core.models import Event
from django.db.models import Q

class EventFilter(django_filters.FilterSet):
    lead = django_filters.NumberFilter(field_name="lead_id")
    date_from = django_filters.DateTimeFilter(
        field_name="quote__event_date",
        lookup_expr="gte"
    )
    date_to = django_filters.DateTimeFilter(
        field_name="quote__event_date",
        lookup_expr="lte"
    )

    class Meta:
        model = Event
        fields = []