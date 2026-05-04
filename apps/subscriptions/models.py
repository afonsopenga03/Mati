# apps/subscriptions/models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta


class Plan(models.Model):
    """Planos SaaS disponíveis na plataforma."""

    TIER_CHOICES = (
        ('TRIAL',      'Trial Grátis'),
        ('BASIC',      'Básico'),
        ('PRO',        'Profissional'),
        ('ENTERPRISE', 'Enterprise'),
    )

    tier = models.CharField(max_length=15, choices=TIER_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Preço anual com desconto (opcional)"
    )
    is_active = models.BooleanField(default=True)

    # ── Limites ─────────────────────────────
    max_customers = models.PositiveIntegerField(
        help_text="0 = ilimitado"
    )
    max_meters = models.PositiveIntegerField(default=0)
    max_users = models.PositiveIntegerField(default=0)
    max_readings_per_month = models.PositiveIntegerField(default=0)
    max_invoices_per_month = models.PositiveIntegerField(default=0)

    # ── Features ─────────────────────────────
    has_api_access = models.BooleanField(default=True)
    has_field_app = models.BooleanField(default=False)
    has_reports = models.BooleanField(default=False)
    has_multi_user = models.BooleanField(default=False)
    has_custom_branding = models.BooleanField(default=False)
    has_priority_support = models.BooleanField(default=False)
    has_data_export = models.BooleanField(default=False)

    # ── Trial ─────────────────────────────────
    trial_days = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['price_monthly']

    def __str__(self):
        return f"{self.name} (MT {self.price_monthly}/mês)"

    def is_unlimited(self, field: str) -> bool:
        return getattr(self, field, 0) == 0


class Subscription(models.Model):
    """Subscrição de uma empresa a um plano."""

    STATUS_CHOICES = (
        ('TRIAL',     'Trial'),
        ('ACTIVE',    'Ativa'),
        ('PAST_DUE',  'Pagamento Pendente'),
        ('SUSPENDED', 'Suspensa'),
        ('CANCELLED', 'Cancelada'),
        ('EXPIRED',   'Expirada'),
    )

    BILLING_CYCLE_CHOICES = (
        ('MONTHLY', 'Mensal'),
        ('YEARLY',  'Anual'),
    )

    company = models.OneToOneField(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='subscription',
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT, related_name='subscriptions'
    )
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default='TRIAL'
    )
    billing_cycle = models.CharField(
        max_length=10, choices=BILLING_CYCLE_CHOICES, default='MONTHLY'
    )

    started_at = models.DateTimeField(auto_now_add=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)

    # Referência de pagamento externo (gateway futuro)
    external_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.company.name} → {self.plan.name} [{self.status}]"

    # ── Propriedades de conveniência ──────────
    @property
    def is_active(self) -> bool:
        return self.status in ('TRIAL', 'ACTIVE')

    @property
    def is_in_trial(self) -> bool:
        return (
            self.status == 'TRIAL'
            and self.trial_ends_at
            and timezone.now() < self.trial_ends_at
        )

    @property
    def days_remaining(self) -> int:
        if self.current_period_end:
            delta = self.current_period_end - timezone.now()
            return max(delta.days, 0)
        if self.is_in_trial and self.trial_ends_at:
            delta = self.trial_ends_at - timezone.now()
            return max(delta.days, 0)
        return 0


class SubscriptionInvoice(models.Model):
    """Faturas SaaS — cobranças de subscrição."""

    STATUS_CHOICES = (
        ('PENDING', 'Pendente'),
        ('PAID',    'Pago'),
        ('FAILED',  'Falhou'),
        ('VOID',    'Anulado'),
    )

    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE,
        related_name='invoices'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='PENDING'
    )
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_ref = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"SaaS Invoice {self.subscription.company.name} — MT {self.amount} [{self.status}]"


class UsageRecord(models.Model):
    """
    Regista o uso mensal de cada empresa.
    Actualizado incrementalmente a cada operação.
    """
    company = models.OneToOneField(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='usage',
    )
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()

    customers_count = models.PositiveIntegerField(default=0)
    meters_count = models.PositiveIntegerField(default=0)
    users_count = models.PositiveIntegerField(default=0)
    readings_this_month = models.PositiveIntegerField(default=0)
    invoices_this_month = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Usage {self.company.name} {self.month:02d}/{self.year}"
