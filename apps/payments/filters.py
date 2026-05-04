# apps/payments/filters.py
import django_filters
from .models import Payment


class PaymentFilter(django_filters.FilterSet):
    method = django_filters.ChoiceFilter(choices=Payment.METHOD_CHOICES)
    status = django_filters.ChoiceFilter(choices=Payment.STATUS_CHOICES)
    date_from = django_filters.DateTimeFilter(
        field_name='payment_date', lookup_expr='gte'
    )
    date_to = django_filters.DateTimeFilter(
        field_name='payment_date', lookup_expr='lte'
    )
    min_amount = django_filters.NumberFilter(
        field_name='amount_paid', lookup_expr='gte'
    )
    max_amount = django_filters.NumberFilter(
        field_name='amount_paid', lookup_expr='lte'
    )
    invoice = django_filters.UUIDFilter(field_name='invoice__id')
    customer = django_filters.UUIDFilter(field_name='invoice__customer__id')

    class Meta:
        model = Payment
        fields = [
            'method', 'status', 'date_from', 'date_to',
            'min_amount', 'max_amount', 'invoice', 'customer',
        ]
