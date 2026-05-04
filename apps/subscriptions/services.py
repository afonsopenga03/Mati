# apps/subscriptions/services.py
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class SubscriptionLimitError(Exception):
    """Lançado quando uma operação excede o limite do plano."""
    def __init__(self, message, limit_type=None, current=None, limit=None):
        super().__init__(message)
        self.limit_type = limit_type
        self.current = current
        self.limit = limit


class SubscriptionService:
    """
    Serviço central de subscrições SaaS.
    Gerencia: criação, trial, upgrade, bloqueio e verificação de limites.
    """

    # ──────────────────────────────────────────
    # Criar subscrição (com trial)
    # ──────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def create_subscription(
        cls,
        company,
        plan,
        billing_cycle: str = 'MONTHLY',
        start_trial: bool = True,
    ):
        from .models import Subscription, UsageRecord

        # Garante que não existe subscrição duplicada
        if hasattr(company, 'subscription'):
            raise ValueError(f"Empresa {company.name} já possui subscrição.")

        now = timezone.now()

        if start_trial and plan.trial_days > 0:
            sub_status = 'TRIAL'
            trial_ends = now + timedelta(days=plan.trial_days)
            period_start = now
            period_end = trial_ends
        else:
            sub_status = 'ACTIVE'
            trial_ends = None
            period_start = now
            period_end = cls._next_period_end(now, billing_cycle)

        subscription = Subscription.objects.create(
            company=company,
            plan=plan,
            status=sub_status,
            billing_cycle=billing_cycle,
            trial_ends_at=trial_ends,
            current_period_start=period_start,
            current_period_end=period_end,
        )

        # Criar registo de uso inicial
        UsageRecord.objects.create(
            company=company,
            month=now.month,
            year=now.year,
        )

        logger.info(
            "Subscrição criada: %s → %s [%s]",
            company.name, plan.name, sub_status,
        )
        return subscription

    # ──────────────────────────────────────────
    # Upgrade / Downgrade
    # ──────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def change_plan(cls, subscription, new_plan, billing_cycle: str = None):
        old_plan = subscription.plan
        subscription.plan = new_plan
        if billing_cycle:
            subscription.billing_cycle = billing_cycle
        if subscription.status == 'TRIAL':
            subscription.status = 'ACTIVE'
            subscription.trial_ends_at = None
        subscription.save()
        logger.info(
            "Plano alterado: %s | %s → %s",
            subscription.company.name, old_plan.name, new_plan.name,
        )
        return subscription

    # ──────────────────────────────────────────
    # Renovação de período
    # ──────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def renew(cls, subscription):
        from .models import SubscriptionInvoice

        now = timezone.now()
        next_end = cls._next_period_end(now, subscription.billing_cycle)

        amount = (
            subscription.plan.price_yearly
            if subscription.billing_cycle == 'YEARLY'
               and subscription.plan.price_yearly
            else subscription.plan.price_monthly
        )

        invoice = SubscriptionInvoice.objects.create(
            subscription=subscription,
            amount=amount,
            status='PENDING',
            period_start=now,
            period_end=next_end,
        )

        subscription.current_period_start = now
        subscription.current_period_end = next_end
        subscription.status = 'ACTIVE'
        subscription.save(update_fields=[
            'current_period_start', 'current_period_end', 'status'
        ])

        return invoice

    # ──────────────────────────────────────────
    # Bloqueio automático
    # ──────────────────────────────────────────
    @classmethod
    def check_and_expire(cls, subscription) -> bool:
        """
        Verifica se subscrição expirou e bloqueia se necessário.
        Retorna True se foi bloqueada agora.
        """
        now = timezone.now()

        if subscription.status == 'TRIAL':
            if subscription.trial_ends_at and now > subscription.trial_ends_at:
                subscription.status = 'EXPIRED'
                subscription.save(update_fields=['status'])
                logger.warning(
                    "Trial expirado: %s", subscription.company.name
                )
                return True

        if subscription.status == 'ACTIVE':
            if subscription.current_period_end and now > subscription.current_period_end:
                subscription.status = 'PAST_DUE'
                subscription.save(update_fields=['status'])
                logger.warning(
                    "Período expirado (PAST_DUE): %s", subscription.company.name
                )
                return True

        return False

    # ──────────────────────────────────────────
    # Verificação de limites
    # ──────────────────────────────────────────
    @classmethod
    def check_limit(cls, company, resource: str):
        """
        Verifica se a empresa pode usar mais um recurso.
        Lança SubscriptionLimitError se excedeu o limite.

        resource: 'customers' | 'meters' | 'users' |
                  'readings' | 'invoices'
        """
        try:
            sub = company.subscription
        except Exception:
            raise SubscriptionLimitError(
                "Esta empresa não possui subscrição activa.",
                limit_type=resource,
            )

        # Bloquear se expirado
        cls.check_and_expire(sub)

        if not sub.is_active:
            raise SubscriptionLimitError(
                f"Subscrição {sub.get_status_display().lower()}. "
                "Por favor renove para continuar.",
                limit_type='subscription',
            )

        plan = sub.plan
        usage = cls._get_or_create_usage(company)

        LIMIT_MAP = {
            'customers': ('max_customers', 'customers_count'),
            'meters':    ('max_meters',    'meters_count'),
            'users':     ('max_users',     'users_count'),
            'readings':  ('max_readings_per_month', 'readings_this_month'),
            'invoices':  ('max_invoices_per_month', 'invoices_this_month'),
        }

        if resource not in LIMIT_MAP:
            return  # recurso sem limite configurado

        plan_field, usage_field = LIMIT_MAP[resource]
        limit = getattr(plan, plan_field, 0)

        if limit == 0:
            return  # 0 = ilimitado

        current = getattr(usage, usage_field, 0)

        if current >= limit:
            raise SubscriptionLimitError(
                f"Limite de {resource} atingido para o plano {plan.name}. "
                f"Você usou {current}/{limit}. Faça upgrade para continuar.",
                limit_type=resource,
                current=current,
                limit=limit,
            )

    @classmethod
    def increment_usage(cls, company, resource: str, amount: int = 1):
        """Incrementa contador de uso."""
        usage = cls._get_or_create_usage(company)
        FIELD_MAP = {
            'customers': 'customers_count',
            'meters':    'meters_count',
            'users':     'users_count',
            'readings':  'readings_this_month',
            'invoices':  'invoices_this_month',
        }
        field = FIELD_MAP.get(resource)
        if field:
            from django.db.models import F
            from .models import UsageRecord
            UsageRecord.objects.filter(pk=usage.pk).update(
                **{field: F(field) + amount}
            )

    # ──────────────────────────────────────────
    # Helpers internos
    # ──────────────────────────────────────────
    @staticmethod
    def _next_period_end(start, billing_cycle: str):
        if billing_cycle == 'YEARLY':
            return start.replace(year=start.year + 1)
        # Mensal: 30 dias
        return start + timedelta(days=30)

    @staticmethod
    def _get_or_create_usage(company):
        from .models import UsageRecord
        now = timezone.now()
        usage, _ = UsageRecord.objects.get_or_create(
            company=company,
            month=now.month,
            year=now.year,
        )
        return usage
