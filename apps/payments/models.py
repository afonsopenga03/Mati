# apps/payments/models.py
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from core.models import TenantModel


class Payment(TenantModel):
    METHOD_CHOICES = (
        ('CASH',        'Dinheiro'),
        ('BANK_TRANSFER', 'Transferência Bancária'),
        ('MPESA',       'M-Pesa'),
        ('EMOLA',       'e-Mola'),
        ('CHEQUE',      'Cheque'),
        ('OTHER',       'Outro'),
    )

    STATUS_CHOICES = (
        ('CONFIRMED',  'Confirmado'),
        ('PENDING',    'Pendente de Confirmação'),
        ('REVERSED',   'Estornado'),
    )

    invoice = models.ForeignKey(
        'billing.Invoice',
        on_delete=models.PROTECT,
        related_name='payments',
    )
    payment_date = models.DateTimeField()
    amount_paid = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='CONFIRMED'
    )

    # Referência externa (número de transação M-Pesa, comprovante bancário, etc.)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    reference_note = models.TextField(blank=True, null=True)

    # Quem registrou
    registered_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='registered_payments',
    )

    # Estorno
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reversed_payments',
    )
    reversal_reason = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return (
            f"Pagamento {self.method} R${self.amount_paid} "
            f"→ Fatura #{self.invoice_id} [{self.status}]"
        )
