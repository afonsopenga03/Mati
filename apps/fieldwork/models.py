# apps/fieldwork/models.py
from django.db import models
from core.models import TenantModel


class Route(TenantModel):
    """Rota de leitura — agrupa medidores para um leiturista."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_routes',
        limit_choices_to={'role': 'READER'},
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class RouteStop(TenantModel):
    """
    Parada individual em uma rota — um medidor com ordem de visita.
    """
    route = models.ForeignKey(
        Route, on_delete=models.CASCADE, related_name='stops'
    )
    meter = models.ForeignKey(
        'meters.WaterMeter', on_delete=models.CASCADE,
        related_name='route_stops'
    )
    order = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['order']
        unique_together = ['route', 'meter']

    def __str__(self):
        return f"{self.route.name} → Stop #{self.order}: {self.meter.serial_number}"


class FieldTask(TenantModel):
    """
    Tarefa atribuída a um técnico de campo.
    Pode ser: leitura, instalação, manutenção, inspeção.
    """
    TYPE_CHOICES = (
        ('READING',      'Leitura de Hidrômetro'),
        ('INSTALLATION', 'Instalação de Medidor'),
        ('MAINTENANCE',  'Manutenção'),
        ('INSPECTION',   'Inspeção'),
        ('DISCONNECT',   'Corte de Fornecimento'),
        ('RECONNECT',    'Religação'),
    )
    STATUS_CHOICES = (
        ('PENDING',     'Pendente'),
        ('IN_PROGRESS', 'Em Andamento'),
        ('COMPLETED',   'Concluída'),
        ('SKIPPED',     'Ignorada'),
        ('FAILED',      'Falhou'),
    )
    PRIORITY_CHOICES = (
        ('LOW',    'Baixa'),
        ('NORMAL', 'Normal'),
        ('HIGH',   'Alta'),
        ('URGENT', 'Urgente'),
    )

    task_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='PENDING'
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default='NORMAL'
    )

    assigned_to = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='field_tasks',
        limit_choices_to={'role__in': ['READER', 'ADMIN', 'CLERK']},
    )
    meter = models.ForeignKey(
        'meters.WaterMeter',
        on_delete=models.PROTECT,
        related_name='tasks',
        null=True, blank=True,
    )
    route = models.ForeignKey(
        Route, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tasks'
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    scheduled_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)

    # Resultado (preenchido pelo técnico)
    completed_at = models.DateTimeField(null=True, blank=True)
    result_notes = models.TextField(blank=True)
    result_image = models.ImageField(
        upload_to='fieldwork/results/', null=True, blank=True
    )

    # Localização GPS registrada no campo
    gps_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    gps_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Controle offline
    # UUID gerado no dispositivo mobile para idempotência
    client_uuid = models.UUIDField(unique=True, null=True, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    device_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['scheduled_date', 'priority', 'order_in_route']

    # Índice auxiliar para ordenar na rota
    order_in_route = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f"[{self.get_task_type_display()}] {self.title} — {self.assigned_to}"


class OfflineSyncLog(TenantModel):
    """
    Log de cada sincronização feita por um dispositivo móvel.
    Útil para auditoria e resolução de conflitos.
    """
    user = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE,
        related_name='sync_logs'
    )
    device_id = models.CharField(max_length=100)
    synced_at = models.DateTimeField(auto_now_add=True)
    tasks_uploaded = models.PositiveIntegerField(default=0)
    readings_uploaded = models.PositiveIntegerField(default=0)
    conflicts = models.JSONField(default=list)
    raw_payload = models.JSONField(default=dict)

    class Meta:
        ordering = ['-synced_at']
