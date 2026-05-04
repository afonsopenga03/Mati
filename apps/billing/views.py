# apps/meters/views.py
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import TenantQuerySetMixin
from core.permissions import IsManager, IsFieldWorker
from core.pagination import StandardResultsPagination
from apps.meters.models import WaterMeter, MeterReading
from apps.billing.serializers import (
    WaterMeterSerializer, WaterMeterListSerializer,
    MeterReadingSerializer,
)
from apps.meters.filters import WaterMeterFilter, MeterReadingFilter
from apps.meters.services import MeterReadingService, ReadingValidationError


from rest_framework import viewsets, filters, status

from rest_framework.decorators import action

from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend



from core.mixins import TenantQuerySetMixin

from core.permissions import IsManager, IsAdminUser

from core.pagination import StandardResultsPagination

from .models import TariffPlan, Invoice, InvoiceItem

from .serializers import (

    TariffPlanSerializer, InvoiceSerializer,

    InvoiceListSerializer, InvoiceCreateWithItemsSerializer,

    InvoiceItemSerializer,

)

from .filters import InvoiceFilter





class TariffPlanViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):

    queryset = TariffPlan.objects.all().order_by('name')

    serializer_class = TariffPlanSerializer

    permission_classes = [IsManager]

    pagination_class = StandardResultsPagination

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = ['name']

    ordering_fields = ['name', 'base_fee', 'cost_per_m3']





class InvoiceViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):

    queryset = (

        Invoice.objects

        .select_related('customer')

        .prefetch_related('items')

        .order_by('-due_date')

    )

    permission_classes = [IsManager]

    pagination_class = StandardResultsPagination

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_class = InvoiceFilter

    search_fields = ['customer__first_name', 'customer__last_name']

    ordering_fields = ['due_date', 'total_amount', 'status']



    def get_serializer_class(self):

        if self.action == 'list':

            return InvoiceListSerializer

        if self.action == 'create':

            return InvoiceCreateWithItemsSerializer

        return InvoiceSerializer



    @action(detail=True, methods=['post'])

    def mark_paid(self, request, pk=None):

        invoice = self.get_object()

        if invoice.status == 'PAID':

            return Response(

                {'error': 'Fatura já está paga.'},

                status=status.HTTP_400_BAD_REQUEST

            )

        invoice.status = 'PAID'

        invoice.save(update_fields=['status'])

        return Response({'status': 'fatura marcada como paga'})



    @action(detail=True, methods=['post'])

    def cancel(self, request, pk=None):

        invoice = self.get_object()

        if invoice.status in ('PAID', 'CANCELLED'):

            return Response(

                {'error': f'Não é possível cancelar uma fatura com status {invoice.status}.'},

                status=status.HTTP_400_BAD_REQUEST

            )

        invoice.status = 'CANCELLED'

        invoice.save(update_fields=['status'])

        return Response({'status': 'fatura cancelada'})



    @action(detail=False, methods=['get'])

    def summary(self, request):

        """Retorna totais agrupados por status para o dashboard."""

        from django.db.models import Sum, Count

        qs = self.get_queryset()

        data = (

            qs.values('status')

            .annotate(

                total_amount=Sum('total_amount'),

                count=Count('id'),

            )

            .order_by('status')

        )

        return Response(list(data))



class WaterMeterViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = (
        WaterMeter.objects
        .select_related('address', 'address__customer')
        .prefetch_related('readings')
        .order_by('serial_number')
    )
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = WaterMeterFilter
    search_fields = ['serial_number']
    ordering_fields = ['serial_number', 'installation_date', 'status']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'readings']:
            return [IsFieldWorker()]
        return [IsManager()]

    def get_serializer_class(self):
        if self.action == 'list':
            return WaterMeterListSerializer
        return WaterMeterSerializer

    # ── Leituras aninhadas ─────────────────────
    @action(detail=True, methods=['get', 'post'], url_path='readings')
    def readings(self, request, pk=None):
        meter = self.get_object()

        if request.method == 'GET':
            qs = meter.readings.all()
            filterset = MeterReadingFilter(request.GET, queryset=qs)
            page = self.paginate_queryset(filterset.qs)
            serializer = MeterReadingSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # POST — usa o service para validar e criar
        serializer = MeterReadingSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        try:
            reading = MeterReadingService.register_reading(
                meter=meter,
                reading_value=serializer.validated_data['reading_value'],
                reading_date=serializer.validated_data.get('reading_date'),
                reader=request.user,
                image_evidence=serializer.validated_data.get('image_evidence'),
            )
        except ReadingValidationError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        out = MeterReadingSerializer(reading)
        return Response(out.data, status=status.HTTP_201_CREATED)

    # ── Ações de status ────────────────────────
    @action(detail=True, methods=['post'])
    def set_maintenance(self, request, pk=None):
        meter = self.get_object()
        meter.status = 'MAINTENANCE'
        meter.save(update_fields=['status'])
        return Response({'status': 'medidor em manutenção'})

    @action(detail=True, methods=['post'])
    def set_active(self, request, pk=None):
        meter = self.get_object()
        meter.status = 'ACTIVE'
        meter.save(update_fields=['status'])
        return Response({'status': 'medidor ativado'})

    # ── Anomalias ──────────────────────────────
    @action(detail=False, methods=['get'])
    def anomalies(self, request):
        """Lista todas as leituras anômalas da empresa."""
        qs = (
            MeterReading.objects
            .filter(
                company=request.user.company,
                anomaly_flag=True,
            )
            .select_related('meter', 'reader')
            .order_by('-reading_date')
        )
        page = self.paginate_queryset(qs)
        serializer = MeterReadingSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
    # Adicionar ao InvoiceViewSet existente:

    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """
        Gera faturas manualmente para um mês/ano.
        Body: { "reference_month": 5, "reference_year": 2025 }
        """
        from .services import InvoiceGenerationService

        month = request.data.get('reference_month')
        year = request.data.get('reference_year')

        if not month or not year:
            return Response(
                {'error': 'Informe reference_month e reference_year.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = InvoiceGenerationService.generate_for_company(
            company=request.user.company,
            reference_month=int(month),
            reference_year=int(year),
        )
        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='apply-late-fees')
    def apply_late_fees(self, request):
        """Aplica multas e juros manualmente."""
        from .services import LateFeeService
        count = LateFeeService.apply_late_fees_for_company(request.user.company)
        return Response({'invoices_updated': count})

    # ── Histórico de consumo ───────────────────
    @action(detail=True, methods=['get'], url_path='consumption-history')
    def consumption_history(self, request, pk=None):
        meter = self.get_object()
        limit = int(request.query_params.get('limit', 12))
        data = MeterReadingService.get_meter_consumption_history(meter, limit=limit)
        return Response(data)
