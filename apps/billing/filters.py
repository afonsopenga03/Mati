# apps/billing/filters.py
import django_filters
from .models import Invoice


class InvoiceFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Invoice.STATUS_CHOICES)
    due_after = django_filters.DateFilter(
        field_name='due_date', lookup_expr='gte'
    )
    due_before = django_filters.DateFilter(
        field_name='due_date', lookup_expr='lte'
    )
    customer = django_filters.UUIDFilter(field_name='customer__id')
    min_amount = django_filters.NumberFilter(
        field_name='total_amount', lookup_expr='gte'
    )
    max_amount = django_filters.NumberFilter(
        field_name='total_amount', lookup_expr='lte'
    )

    class Meta:
        model = Invoice
        fields = [
            'status', 'due_after', 'due_before',
            'customer', 'min_amount', 'max_amount',
        ]
