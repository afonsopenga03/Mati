# apps/payments/services.py
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    pass


class PaymentService:
    """
    Camada de serviço completa para pagamentos.
    Suporta: pagamentos parciais, múltiplos métodos, estorno.
    """

    # ──────────────────────────────────────────
    # Registrar pagamento
    # ──────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def register_payment(
        cls,
        invoice,
        amount_paid: Decimal,
        method: str,
        payment_date=None,
        transaction_id: str = None,
        reference_note: str = None,
        registered_by=None,
    ):
        """
        Registra um pagamento (total ou parcial) para uma fatura.
        Atualiza o status da fatura automaticamente.
        Retorna o objeto Payment criado.
        """
        from .models import Payment

        if payment_date is None:
            payment_date = timezone.now()

        # Validações de negócio
        cls._validate_invoice_payable(invoice)
        cls._validate_amount(invoice, amount_paid)

        # Criar pagamento
        payment = Payment.objects.create(
            invoice=invoice,
            company=invoice.company,
            amount_paid=amount_paid,
            method=method,
            payment_date=payment_date,
            transaction_id=transaction_id,
            reference_note=reference_note,
            registered_by=registered_by,
            status='CONFIRMED',
        )

        # Atualizar status da fatura
        cls._update_invoice_status(invoice)

        logger.info(
            "Pagamento %s registrado: R$%s via %s → Fatura %s",
            payment.pk, amount_paid, method, invoice.pk,
        )
        return payment

    # ──────────────────────────────────────────
    # Estornar pagamento
    # ──────────────────────────────────────────
    @classmethod
    @transaction.atomic
    def reverse_payment(cls, payment, reason: str, reversed_by=None):
        """
        Estorna um pagamento confirmado.
        Reverte o status da fatura para PENDING/OVERDUE.
        """
        if payment.status == 'REVERSED':
            raise PaymentError("Este pagamento já foi estornado.")

        payment.status = 'REVERSED'
        payment.reversed_at = timezone.now()
        payment.reversed_by = reversed_by
        payment.reversal_reason = reason
        payment.save(update_fields=[
            'status', 'reversed_at', 'reversed_by', 'reversal_reason'
        ])

        # Recalcula status da fatura
        cls._update_invoice_status(payment.invoice)

        logger.info("Pagamento %s estornado por %s.", payment.pk, reversed_by)
        return payment

    # ──────────────────────────────────────────
    # Resumo financeiro de uma fatura
    # ──────────────────────────────────────────
    @staticmethod
    def get_invoice_payment_summary(invoice) -> dict:
        """
        Retorna o resumo de pagamentos de uma fatura:
        total pago, saldo restante, lista de pagamentos confirmados.
        """
        confirmed = invoice.payments.filter(status='CONFIRMED')
        total_paid = sum(p.amount_paid for p in confirmed) or Decimal('0')
        balance = invoice.total_amount - total_paid

        return {
            'total_amount': float(invoice.total_amount),
            'total_paid': float(total_paid),
            'balance_due': float(max(balance, Decimal('0'))),
            'is_fully_paid': balance <= 0,
            'payment_count': confirmed.count(),
        }

    # ──────────────────────────────────────────
    # Validações internas
    # ──────────────────────────────────────────
    @staticmethod
    def _validate_invoice_payable(invoice):
        if invoice.status == 'CANCELLED':
            raise PaymentError(
                "Não é possível registrar pagamento em fatura cancelada."
            )
        if invoice.status == 'PAID':
            raise PaymentError(
                "Esta fatura já está totalmente paga."
            )

    @staticmethod
    def _validate_amount(invoice, amount: Decimal):
        if amount <= 0:
            raise PaymentError("O valor do pagamento deve ser maior que zero.")

        confirmed = invoice.payments.filter(status='CONFIRMED')
        total_paid = sum(p.amount_paid for p in confirmed) or Decimal('0')
        balance = invoice.total_amount - total_paid

        if amount > balance:
            raise PaymentError(
                f"Valor informado (R${amount}) excede o saldo devedor "
                f"(R${balance:.2f}). Use no máximo R${balance:.2f}."
            )

    @staticmethod
    def _update_invoice_status(invoice):
        """
        Recalcula e salva o status da fatura com base nos pagamentos confirmados.
        """
        from django.utils import timezone as tz

        confirmed = invoice.payments.filter(status='CONFIRMED')
        total_paid = sum(p.amount_paid for p in confirmed) or Decimal('0')
        today = tz.now().date()

        if total_paid >= invoice.total_amount:
            new_status = 'PAID'
        elif invoice.due_date < today:
            new_status = 'OVERDUE'
        else:
            new_status = 'PENDING'

        invoice.status = new_status
        invoice.save(update_fields=['status'])
