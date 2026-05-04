# apps/meters/filters.py
import django_filters
from .models import WaterMeter, MeterReading


class WaterMeterFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=WaterMeter.STATUS_CHOICES)
    installed_after = django_filters.DateFilter(
        field_name='installation_date', lookup_expr='gte'
    )
    installed_before = django_filters.DateFilter(
        field_name='installation_date', lookup_expr='lte'
    )
    city = django_filters.CharFilter(
        field_name='address__city', lookup_expr='icontains'
    )

    class Meta:
        model = WaterMeter
        fields = ['status', 'installed_after', 'installed_before', 'city']


class MeterReadingFilter(django_filters.FilterSet):
    date_from = django_filters.DateTimeFilter(
        field_name='reading_date', lookup_expr='gte'
    )
    date_to = django_filters.DateTimeFilter(
        field_name='reading_date', lookup_expr='lte'
    )

    class Meta:
        model = MeterReading
        fields = ['date_from', 'date_to']
