# apps/payments/views.py
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count

from core.mixins import TenantQuerySetMixin
from core.permissions import IsManager
from core.pagination import StandardResultsPagination
from .models import Payment
from apps.payments.serializers import (
    PaymentSerializer, PaymentListSerializer, ReversalSerializer
)
from .filters import PaymentFilter
from .services import PaymentService, PaymentError


class PaymentViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """
    Pagamentos: criação via service, sem edição (imutável após confirmado).
    Suporta: listagem, detalhe, criação, estorno.
    """
    queryset = (
        Payment.objects
        .select_related('invoice', 'invoice__customer', 'registered_by')
        .order_by('-payment_date')
    )
    permission_classes = [IsManager]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PaymentFilter
    search_fields = [
        'invoice__customer__first_name',
        'invoice__customer__last_name',
        'transaction_id',
    ]
    ordering_fields = ['payment_date', 'amount_paid', 'method']
    # Sem PUT/PATCH/DELETE — pagamentos são imutáveis (só estorno)
    http_method_names = ['get', 'post', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'list':
            return PaymentListSerializer
        return PaymentSerializer

    def create(self, request, *args, **kwargs):
        serializer = PaymentSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        try:
            payment = PaymentService.register_payment(
                invoice=vd['invoice'],
                amount_paid=vd['amount_paid'],
                method=vd['method'],
                payment_date=vd.get('payment_date'),
                transaction_id=vd.get('transaction_id'),
                reference_note=vd.get('reference_note'),
                registered_by=request.user,
            )
        except PaymentError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        out = PaymentSerializer(payment, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    # ── Estorno ────────────────────────────────
    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """Estorna um pagamento confirmado."""
        payment = self.get_object()
        serializer = ReversalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            PaymentService.reverse_payment(
                payment=payment,
                reason=serializer.validated_data['reason'],
                reversed_by=request.user,
            )
        except PaymentError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        out = PaymentSerializer(payment, context={'request': request})
        return Response(out.data)

    # ── Resumo por fatura ──────────────────────
    @action(detail=False, methods=['get'], url_path='by-invoice/(?P<invoice_pk>[^/.]+)')
    def by_invoice(self, request, invoice_pk=None):
        """Histórico completo de pagamentos de uma fatura."""
        from billing.models import Invoice
        try:
            invoice = Invoice.objects.get(
                pk=invoice_pk, company=request.user.company
            )
        except Invoice.DoesNotExist:
            return Response(
                {'error': 'Fatura não encontrada.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        payments = invoice.payments.select_related('registered_by')
        summary = PaymentService.get_invoice_payment_summary(invoice)

        return Response({
            'invoice': {
                'id': str(invoice.pk),
                'total_amount': float(invoice.total_amount),
                'status': invoice.status,
                'reference': f"{invoice.reference_month:02d}/{invoice.reference_year}",
            },
            'summary': summary,
            'payments': PaymentSerializer(
                payments, many=True, context={'request': request}
            ).data,
        })

    # ── Dashboard de pagamentos ────────────────
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Totais de pagamentos por método e por status."""
        qs = self.get_queryset().filter(status='CONFIRMED')

        by_method = list(
            qs.values('method')
            .annotate(total=Sum('amount_paid'), count=Count('id'))
            .order_by('method')
        )
        total_confirmed = qs.aggregate(
            total=Sum('amount_paid'), count=Count('id')
        )

        return Response({
            'total_confirmed': {
                'amount': float(total_confirmed['total'] or 0),
                'count': total_confirmed['count'],
            },
            'by_method': [
                {
                    'method': item['method'],
                    'method_display': dict(Payment.METHOD_CHOICES).get(item['method']),
                    'total': float(item['total']),
                    'count': item['count'],
                }
                for item in by_method
            ],
        })
