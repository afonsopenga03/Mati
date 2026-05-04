# apps/fieldwork/services.py
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class OfflineSyncError(Exception):
    pass


class FieldTaskService:

    @classmethod
    def get_worker_bundle(cls, user) -> dict:
        """
        Retorna o pacote completo de dados para o dispositivo móvel:
        tarefas pendentes + medidores + clientes + últimas leituras.
        Compacto para economizar banda.
        """
        from .models import FieldTask, Route
        from meters.models import WaterMeter

        today = timezone.now().date()

        tasks = (
            FieldTask.objects
            .filter(
                company=user.company,
                assigned_to=user,
                status__in=['PENDING', 'IN_PROGRESS'],
                scheduled_date__lte=today,
            )
            .select_related('meter', 'meter__address', 'meter__address__customer', 'route')
            .order_by('scheduled_date', 'order_in_route')
        )

        return {
            'generated_at': timezone.now().isoformat(),
            'worker': {
                'id': str(user.pk),
                'name': user.get_full_name(),
                'username': user.username,
            },
            'tasks': [cls._serialize_task_for_mobile(t) for t in tasks],
        }

    @staticmethod
    def _serialize_task_for_mobile(task) -> dict:
        meter = task.meter
        customer = meter.address.customer if meter else None
        last_reading = (
            meter.readings.first() if meter else None
        )

        return {
            'id': str(task.pk),
            'client_uuid': str(task.client_uuid) if task.client_uuid else None,
            'type': task.task_type,
            'status': task.status,
            'priority': task.priority,
            'title': task.title,
            'description': task.description,
            'scheduled_date': task.scheduled_date.isoformat(),
            'meter': {
                'id': str(meter.pk),
                'serial_number': meter.serial_number,
                'status': meter.status,
                'last_reading': {
                    'value': float(last_reading.reading_value),
                    'date': last_reading.reading_date.isoformat(),
                } if last_reading else None,
            } if meter else None,
            'customer': {
                'id': str(customer.pk),
                'name': f"{customer.first_name} {customer.last_name}",
                'document_id': customer.document_id,
                'address': {
                    'street': meter.address.street,
                    'number': meter.address.number,
                    'neighborhood': meter.address.neighborhood,
                    'city': meter.address.city,
                    'latitude': float(meter.address.latitude) if meter.address.latitude else None,
                    'longitude': float(meter.address.longitude) if meter.address.longitude else None,
                },
            } if customer else None,
            'result_notes': task.result_notes,
        }


class OfflineSyncService:
    """
    Processa o payload de sincronização vindo do app móvel.
    Implementa idempotência via client_uuid.
    """

    @classmethod
    @transaction.atomic
    def process_sync(cls, user, payload: dict) -> dict:
        """
        payload = {
          "device_id": "...",
          "tasks": [...],
          "readings": [...],
        }
        """
        from .models import OfflineSyncLog

        device_id = payload.get('device_id', 'unknown')
        tasks_payload = payload.get('tasks', [])
        readings_payload = payload.get('readings', [])

        results = {
            'tasks': {'created': 0, 'updated': 0, 'errors': []},
            'readings': {'created': 0, 'errors': []},
            'conflicts': [],
        }

        # Processar tarefas
        for task_data in tasks_payload:
            try:
                result = cls._sync_task(user, task_data)
                if result == 'created':
                    results['tasks']['created'] += 1
                else:
                    results['tasks']['updated'] += 1
            except Exception as exc:
                logger.exception("Erro sync task %s: %s", task_data.get('client_uuid'), exc)
                results['tasks']['errors'].append({
                    'client_uuid': task_data.get('client_uuid'),
                    'error': str(exc),
                })

        # Processar leituras
        for reading_data in readings_payload:
            try:
                cls._sync_reading(user, reading_data)
                results['readings']['created'] += 1
            except Exception as exc:
                logger.exception("Erro sync reading: %s", exc)
                results['readings']['errors'].append({
                    'meter': reading_data.get('meter_id'),
                    'error': str(exc),
                })

        # Log
        OfflineSyncLog.objects.create(
            company=user.company,
            user=user,
            device_id=device_id,
            tasks_uploaded=len(tasks_payload),
            readings_uploaded=len(readings_payload),
            conflicts=results['conflicts'],
            raw_payload=payload,
        )

        return results

    @staticmethod
    def _sync_task(user, data: dict) -> str:
        from .models import FieldTask

        client_uuid = data.get('client_uuid')
        task_id = data.get('id')
        now = timezone.now()

        # Idempotência: se já existe com este client_uuid, atualizar
        existing = None
        if client_uuid:
            existing = FieldTask.objects.filter(client_uuid=client_uuid).first()
        if not existing and task_id:
            try:
                existing = FieldTask.objects.get(pk=task_id, company=user.company)
            except FieldTask.DoesNotExist:
                pass

        if existing:
            # Só atualiza se o status é válido (não regride)
            STATUS_ORDER = {
                'PENDING': 0, 'IN_PROGRESS': 1,
                'COMPLETED': 2, 'SKIPPED': 2, 'FAILED': 2,
            }
            incoming_status = data.get('status', existing.status)
            if STATUS_ORDER.get(incoming_status, 0) >= STATUS_ORDER.get(existing.status, 0):
                existing.status = incoming_status
                existing.result_notes = data.get('result_notes', existing.result_notes)
                existing.gps_latitude = data.get('gps_latitude')
                existing.gps_longitude = data.get('gps_longitude')
                existing.device_id = data.get('device_id', '')
                existing.synced_at = now
                if incoming_status == 'COMPLETED' and not existing.completed_at:
                    existing.completed_at = now
                existing.save()
            return 'updated'

        return 'skipped'

    @staticmethod
    def _sync_reading(user, data: dict):
        """Registra leitura vinda do dispositivo offline."""
        from meters.models import WaterMeter
        from meters.services import MeterReadingService, ReadingValidationError
        from django.utils.dateparse import parse_datetime

        meter = WaterMeter.objects.get(pk=data['meter_id'], company=user.company)
        reading_value = Decimal(str(data['reading_value']))
        reading_date = parse_datetime(data['reading_date']) or timezone.now()

        MeterReadingService.register_reading(
            meter=meter,
            reading_value=reading_value,
            reading_date=reading_date,
            reader=user,
        )
