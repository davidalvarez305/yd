import django_filters
from core.models import Service

class ServiceFilter(django_filters.FilterSet):
    service = django_filters.CharFilter(
        field_name="service",
        lookup_expr="icontains"
    )

    service_type = django_filters.CharFilter(
        field_name="service_type__type",
        lookup_expr="icontains"
    )

    class Meta:
        model = Service
        fields = ["service_type"]