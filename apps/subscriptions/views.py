# apps/subscriptions/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from core.permissions import IsAdminUser
from .models import Plan, Subscription, SubscriptionInvoice
from apps.subscriptions.serializers import (
    PlanSerializer, SubscriptionSerializer,
    SubscriptionInvoiceSerializer, ChangePlanSerializer,
    SubscriptionInvoicePaySerializer,
)
from .services import SubscriptionService


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """Listagem pública de planos disponíveis."""
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]


class SubscriptionViewSet(viewsets.GenericViewSet):
    """
    Gestão da subscrição da empresa do utilizador autenticado.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SubscriptionSerializer

    def get_subscription(self):
        company = self.request.user.company
        if not company:
            return None
        try:
            return company.subscription
        except Subscription.DoesNotExist:
            return None

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Estado actual da subscrição + uso."""
        sub = self.get_subscription()
        if not sub:
            return Response(
                {'error': 'Sem subscrição activa.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        SubscriptionService.check_and_expire(sub)
        return Response(SubscriptionSerializer(sub).data)

    @action(detail=False, methods=['get'])
    def usage(self, request):
        """Uso actual vs limites do plano."""
        company = request.user.company
        if not company:
            return Response({'error': 'Sem empresa.'}, status=404)

        try:
            sub = company.subscription
        except Subscription.DoesNotExist:
            return Response({'error': 'Sem subscrição.'}, status=404)

        from .services import SubscriptionService
        usage = SubscriptionService._get_or_create_usage(company)
        plan = sub.plan

        def pct(current, limit):
            if limit == 0:
                return None  # ilimitado
            return round((current / limit) * 100, 1)

        return Response({
            'plan': plan.name,
            'status': sub.status,
            'days_remaining': sub.days_remaining,
            'resources': {
                'customers': {
                    'used': usage.customers_count,
                    'limit': plan.max_customers,
                    'unlimited': plan.max_customers == 0,
                    'percentage': pct(usage.customers_count, plan.max_customers),
                },
                'meters': {
                    'used': usage.meters_count,
                    'limit': plan.max_meters,
                    'unlimited': plan.max_meters == 0,
                    'percentage': pct(usage.meters_count, plan.max_meters),
                },
                'users': {
                    'used': usage.users_count,
                    'limit': plan.max_users,
                    'unlimited': plan.max_users == 0,
                    'percentage': pct(usage.users_count, plan.max_users),
                },
                'readings_this_month': {
                    'used': usage.readings_this_month,
                    'limit': plan.max_readings_per_month,
                    'unlimited': plan.max_readings_per_month == 0,
                    'percentage': pct(
                        usage.readings_this_month,
                        plan.max_readings_per_month
                    ),
                },
                'invoices_this_month': {
                    'used': usage.invoices_this_month,
                    'limit': plan.max_invoices_per_month,
                    'unlimited': plan.max_invoices_per_month == 0,
                    'percentage': pct(
                        usage.invoices_this_month,
                        plan.max_invoices_per_month
                    ),
                },
            },
        })

    @action(detail=False, methods=['post'], url_path='change-plan')
    def change_plan(self, request):
        """Upgrade ou downgrade de plano."""
        serializer = ChangePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sub = self.get_subscription()
        if not sub:
            return Response({'error': 'Sem subscrição.'}, status=404)

        new_plan = serializer.validated_data['plan']
        billing_cycle = serializer.validated_data.get(
            'billing_cycle', sub.billing_cycle
        )

        sub = SubscriptionService.change_plan(sub, new_plan, billing_cycle)
        return Response(SubscriptionSerializer(sub).data)

    @action(detail=False, methods=['post'])
    def cancel(self, request):
        """Cancela a subscrição no fim do período."""
        sub = self.get_subscription()
        if not sub:
            return Response({'error': 'Sem subscrição.'}, status=404)
        if sub.status == 'CANCELLED':
            return Response({'error': 'Já cancelada.'}, status=400)

        sub.status = 'CANCELLED'
        sub.cancelled_at = __import__('django.utils.timezone', fromlist=['timezone']).timezone.now()
        sub.save(update_fields=['status', 'cancelled_at'])
        return Response({'status': 'subscrição cancelada'})

    @action(detail=False, methods=['get'])
    def invoices(self, request):
        """Histórico de faturas SaaS."""
        sub = self.get_subscription()
        if not sub:
            return Response([], status=200)
        invs = sub.invoices.all()
        return Response(SubscriptionInvoiceSerializer(invs, many=True).data)

    @action(detail=False, methods=['post'], url_path='invoices/(?P<inv_pk>[^/.]+)/pay')
    def pay_invoice(self, request, inv_pk=None):
        """Marca uma fatura SaaS como paga e renova a subscrição."""
        sub = self.get_subscription()
        try:
            invoice = sub.invoices.get(pk=inv_pk, status='PENDING')
        except Exception:
            return Response({'error': 'Fatura não encontrada.'}, status=404)

        ser = SubscriptionInvoicePaySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data

        from django.utils import timezone as tz
        invoice.status = 'PAID'
        invoice.paid_at = tz.now()
        invoice.payment_method = vd.get('payment_method', '')
        invoice.transaction_ref = vd.get('transaction_ref', '')
        invoice.save()

        # Renovar período
        SubscriptionService.renew(sub)
        return Response({'status': 'pago', 'invoice_id': str(invoice.pk)})
