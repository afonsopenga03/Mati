# apps/billing/models.py
from django.db import models
from core.models import TenantModel


class TariffPlan(TenantModel):
    name = models.CharField(max_length=100)
    base_fee = models.DecimalField(max_digits=10, decimal_places=2)
    cost_per_m3 = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    # Impostos (percentuais, ex: 0.05 = 5%)
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=4, default=0,
        help_text="Taxa de imposto (ex: 0.05 para 5%)"
    )
    # Multa por atraso (percentual aplicado ao total)
    late_fee_rate = models.DecimalField(
        max_digits=5, decimal_places=4, default=0,
        help_text="Multa por atraso (ex: 0.02 para 2%)"
    )
    # Juros diários por atraso (ex: 0.00033 ≈ 1%/mês)
    daily_interest_rate = models.DecimalField(
        max_digits=8, decimal_places=6, default=0,
        help_text="Juros diários por atraso"
    )

    def __str__(self):
        return self.name


class TariffBracket(TenantModel):
    """
    Escalões de consumo. Ex:
      0–10 m³  → R$ 1,50/m³
      10–20 m³ → R$ 2,50/m³
      20+  m³  → R$ 4,00/m³
    """
    tariff_plan = models.ForeignKey(
        TariffPlan, on_delete=models.CASCADE, related_name='brackets'
    )
    min_m3 = models.DecimalField(max_digits=10, decimal_places=3)
    max_m3 = models.DecimalField(
        max_digits=10, decimal_places=3,
        null=True, blank=True,
        help_text="Null = sem limite superior"
    )
    price_per_m3 = models.DecimalField(max_digits=10, decimal_places=4)

    class Meta:
        ordering = ['min_m3']

    def __str__(self):
        top = f"{self.max_m3}" if self.max_m3 else "∞"
        return f"{self.tariff_plan.name}: {self.min_m3}–{top} m³ @ {self.price_per_m3}/m³"


class Invoice(TenantModel):
    STATUS_CHOICES = (
        ('PENDING', 'Pendente'),
        ('PAID', 'Pago'),
        ('OVERDUE', 'Atrasado'),
        ('CANCELLED', 'Cancelado'),
    )

    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.PROTECT,
        related_name='invoices'
    )
    tariff_plan = models.ForeignKey(
        TariffPlan, on_delete=models.PROTECT,
        null=True, blank=True
    )

    # Período de referência
    reference_month = models.PositiveSmallIntegerField()   # 1–12
    reference_year = models.PositiveSmallIntegerField()

    due_date = models.DateField()

    # Valores
    consumption_m3 = models.DecimalField(
        max_digits=12, decimal_places=3, default=0
    )
    base_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    consumption_charge = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    late_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='PENDING'
    )
    pdf_file = models.FileField(upload_to='invoices/', null=True, blank=True)

    class Meta:
        unique_together = ['company', 'customer', 'reference_month', 'reference_year']

    def __str__(self):
        return f"Fatura {self.customer} {self.reference_month:02d}/{self.reference_year}"


class InvoiceItem(TenantModel):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name='items'
    )
    description = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(max_digits=10, decimal_places=4)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return self.description
