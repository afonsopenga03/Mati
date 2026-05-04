# apps/subscriptions/tasks.py
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_expired_subscriptions():
    """
    Verifica e expira subscrições diariamente.
    Celery beat: todos os dias às 01:00.
    """
    from .models import Subscription
    from .services import SubscriptionService

    active_subs = Subscription.objects.filter(
        status__in=['TRIAL', 'ACTIVE', 'PAST_DUE']
    ).select_related('company', 'plan')

    expired = 0
    for sub in active_subs:
        was_expired = SubscriptionService.check_and_expire(sub)
        if was_expired:
            expired += 1
            _notify_expiry(sub)

    logger.info("Subscrições expiradas: %d", expired)
    return {'expired': expired}


@shared_task
def generate_saas_invoices():
    """
    Gera faturas SaaS para subscrições a vencer em 3 dias.
    Celery beat: todos os dias às 08:00.
    """
    from .models import Subscription
    from .services import SubscriptionService
    from datetime import timedelta

    now = timezone.now()
    threshold = now + timedelta(days=3)

    due_subs = Subscription.objects.filter(
        status='ACTIVE',
        current_period_end__lte=threshold,
        current_period_end__gt=now,
    ).select_related('company', 'plan')

    created = 0
    for sub in due_subs:
        invoice = SubscriptionService.renew(sub)
        if invoice:
            created += 1
            logger.info("SaaS invoice gerada para %s", sub.company.name)

    return {'invoices_created': created}


@shared_task
def reset_monthly_usage():
    """
    Reseta contadores mensais no 1º dia de cada mês.
    Celery beat: dia 1 às 00:30.
    """
    from .models import UsageRecord
    from django.utils import timezone as tz

    now = tz.now()
    UsageRecord.objects.filter(
        month=now.month,
        year=now.year,
    ).update(
        readings_this_month=0,
        invoices_this_month=0,
    )
    logger.info("Contadores mensais resetados para %d/%d", now.month, now.year)


def _notify_expiry(subscription):
    """Placeholder para envio de email/SMS ao expirar."""
    logger.warning(
        "NOTIFICAÇÃO EXPIRAÇÃO: %s — plano %s expirou.",
        subscription.company.name,
        subscription.plan.name,
    )
