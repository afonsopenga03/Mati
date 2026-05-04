# apps/meters/views.py
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import TenantQuerySetMixin
from core.permissions import IsManager, IsFieldWorker
from core.pagination import StandardResultsPagination
from .models import WaterMeter, MeterReading
from .serializers import (
    WaterMeterSerializer, WaterMeterListSerializer,
    MeterReadingSerializer,
)
from .filters import WaterMeterFilter, MeterReadingFilter
from .services import MeterReadingService, ReadingValidationError


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

    # ── Histórico de consumo ───────────────────
    @action(detail=True, methods=['get'], url_path='consumption-history')
    def consumption_history(self, request, pk=None):
        meter = self.get_object()
        limit = int(request.query_params.get('limit', 12))
        data = MeterReadingService.get_meter_consumption_history(meter, limit=limit)
        return Response(data)
