# apps/fieldwork/views.py
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from core.mixins import TenantQuerySetMixin
from core.permissions import IsManager, IsFieldWorker
from core.pagination import StandardResultsPagination
from .models import Route, RouteStop, FieldTask, OfflineSyncLog
from .serializers import (
    RouteSerializer, RouteListSerializer,
    FieldTaskSerializer, FieldTaskCompleteSerializer,
    OfflineSyncSerializer, RouteStopSerializer,
)
from .services import FieldTaskService, OfflineSyncService


class RouteViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD de rotas de leitura."""
    queryset = (
        Route.objects
        .select_related('assigned_to')
        .prefetch_related('stops', 'stops__meter', 'stops__meter__address',
                          'stops__meter__address__customer')
        .order_by('name')
    )
    permission_classes = [IsManager]
    pagination_class = StandardResultsPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return RouteListSerializer
        return RouteSerializer

    @action(detail=True, methods=['post'], url_path='add-stop')
    def add_stop(self, request, pk=None):
        """Adiciona um medidor à rota."""
        route = self.get_object()
        serializer = RouteStopSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stop = serializer.save(route=route, company=route.company)
        return Response(
            RouteStopSerializer(stop).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='reorder')
    def reorder(self, request, pk=None):
        """
        Reordena as paradas.
        Body: {"order": ["stop_id_1", "stop_id_2", ...]}
        """
        route = self.get_object()
        order = request.data.get('order', [])
        for idx, stop_id in enumerate(order):
            RouteStop.objects.filter(pk=stop_id, route=route).update(order=idx)
        return Response({'status': 'rota reordenada'})

    @action(detail=True, methods=['get'], url_path='generate-tasks')
    def generate_tasks(self, request, pk=None):
        """
        Gera tarefas de leitura para todos os medidores da rota
        para a data informada (default: hoje).
        """
        from .models import FieldTask
        import datetime

        route = self.get_object()
        date_str = request.query_params.get('date')
        scheduled_date = (
            datetime.date.fromisoformat(date_str)
            if date_str else timezone.now().date()
        )

        created = 0
        for stop in route.stops.select_related('meter'):
            _, created_flag = FieldTask.objects.get_or_create(
                company=route.company,
                meter=stop.meter,
                route=route,
                task_type='READING',
                scheduled_date=scheduled_date,
                defaults={
                    'title': f'Leitura — {stop.meter.serial_number}',
                    'assigned_to': route.assigned_to or request.user,
                    'priority': 'NORMAL',
                    'order_in_route': stop.order,
                    'status': 'PENDING',
                }
            )
            if created_flag:
                created += 1

        return Response({
            'tasks_created': created,
            'scheduled_date': scheduled_date.isoformat(),
        })


class FieldTaskViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """Gestão de tarefas de campo."""
    queryset = (
        FieldTask.objects
        .select_related('assigned_to', 'meter', 'meter__address',
                        'meter__address__customer', 'route')
        .order_by('scheduled_date', 'order_in_route')
    )
    pagination_class = StandardResultsPagination
    filter_backends = [
        DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter
    ]
    filterset_fields = ['status', 'task_type', 'priority', 'assigned_to']
    search_fields = ['title', 'meter__serial_number']
    ordering_fields = ['scheduled_date', 'priority', 'status']
    serializer_class = FieldTaskSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'my_tasks',
                           'complete', 'start', 'bundle']:
            return [IsFieldWorker()]
        return [IsManager()]

    # ── Endpoint mobile: bundle completo ──────
    @action(detail=False, methods=['get'])
    def bundle(self, request):
        """
        Retorna o pacote de dados para o app móvel offline.
        Inclui todas as tarefas pendentes + dados de medidores/clientes.
        """
        data = FieldTaskService.get_worker_bundle(request.user)
        return Response(data)

    # ── Minhas tarefas (leiturista) ───────────
    @action(detail=False, methods=['get'], url_path='my-tasks')
    def my_tasks(self, request):
        """Lista as tarefas do usuário autenticado."""
        qs = self.get_queryset().filter(assigned_to=request.user)

        # Filtros opcionais
        task_status = request.query_params.get('status')
        if task_status:
            qs = qs.filter(status=task_status)

        date_filter = request.query_params.get('date')
        if date_filter:
            qs = qs.filter(scheduled_date=date_filter)

        page = self.paginate_queryset(qs)
        serializer = FieldTaskSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    # ── Iniciar tarefa ────────────────────────
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        task = self.get_object()
        if task.status != 'PENDING':
            return Response(
                {'error': f'Tarefa já está com status {task.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task.status = 'IN_PROGRESS'
        task.save(update_fields=['status'])
        return Response(FieldTaskSerializer(task).data)

    # ── Concluir tarefa ───────────────────────
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        serializer = FieldTaskCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        task.status = 'COMPLETED'
        task.completed_at = timezone.now()
        task.result_notes = vd.get('result_notes', '')
        task.gps_latitude = vd.get('gps_latitude')
        task.gps_longitude = vd.get('gps_longitude')
        if vd.get('result_image'):
            task.result_image = vd['result_image']
        task.save()

        return Response(FieldTaskSerializer(task).data)

    # ── Ignorar tarefa ────────────────────────
    @action(detail=True, methods=['post'])
    def skip(self, request, pk=None):
        task = self.get_object()
        reason = request.data.get('reason', '')
        task.status = 'SKIPPED'
        task.result_notes = reason
        task.save(update_fields=['status', 'result_notes'])
        return Response(FieldTaskSerializer(task).data)

    # ── Sincronização offline ─────────────────
    @action(detail=False, methods=['post'])
    def sync(self, request):
        """
        Endpoint de sincronização offline.
        Recebe payload do app móvel e processa em batch.
        """
        serializer = OfflineSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        results = OfflineSyncService.process_sync(
            user=request.user,
            payload=serializer.validated_data,
        )
        return Response(results, status=status.HTTP_200_OK)

    # ── Dashboard de produtividade ────────────
    @action(detail=False, methods=['get'])
    def productivity(self, request):
        """Resumo de produtividade por técnico."""
        from django.db.models import Count, Q
        import datetime

        today = timezone.now().date()
        week_start = today - datetime.timedelta(days=today.weekday())

        qs = self.get_queryset()

        summary = (
            qs.values('assigned_to__first_name', 'assigned_to__last_name')
            .annotate(
                total=Count('id'),
                completed=Count('id', filter=Q(status='COMPLETED')),
                pending=Count('id', filter=Q(status='PENDING')),
                skipped=Count('id', filter=Q(status='SKIPPED')),
            )
            .order_by('-completed')
        )

        return Response(list(summary))
