# apps/customers/filters.py
import django_filters
from .models import Customer


class CustomerFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter()
    city = django_filters.CharFilter(
        field_name='addresses__city',
        lookup_expr='icontains'
    )
    created_after = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='date__gte'
    )
    created_before = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='date__lte'
    )

    class Meta:
        model = Customer
        fields = ['is_active', 'city', 'created_after', 'created_before']
