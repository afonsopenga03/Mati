# apps/billing/services.py
from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Cálculo de Tarifa
# ──────────────────────────────────────────────────────────────

class TariffCalculator:
    """
    Calcula o valor de consumo aplicando escalões progressivos.
    Suporta tanto tarifa simples (custo_por_m3) como escalões (brackets).
    """

    @classmethod
    def calculate_consumption_charge(
        cls,
        tariff_plan,
        consumption_m3: Decimal
    ) -> dict:
        """
        Retorna:
          - total_charge: valor total dos escalões
          - breakdown: lista de itens (escalão, m3 usados, valor)
        """
        brackets = list(tariff_plan.brackets.order_by('min_m3'))

        if brackets:
            return cls._apply_brackets(brackets, consumption_m3)
        else:
            # Tarifa simples sem escalões
            charge = (consumption_m3 * tariff_plan.cost_per_m3).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            return {
                'total_charge': charge,
                'breakdown': [{
                    'description': f'Consumo {consumption_m3} m³ × R$ {tariff_plan.cost_per_m3}/m³',
                    'quantity': float(consumption_m3),
                    'unit_price': float(tariff_plan.cost_per_m3),
                    'subtotal': float(charge),
                }],
            }

    @staticmethod
    def _apply_brackets(brackets, consumption_m3: Decimal) -> dict:
        """Aplica escalões progressivos (como alíquotas progressivas do IR)."""
        remaining = consumption_m3
        total = Decimal('0')
        breakdown = []

        for bracket in brackets:
            if remaining <= 0:
                break

            bracket_start = bracket.min_m3
            bracket_end = bracket.max_m3  # None = ilimitado

            if bracket_end is not None:
                bracket_width = bracket_end - bracket_start
            else:
                bracket_width = remaining  # consome tudo no último escalão

            volume_in_bracket = min(remaining, bracket_width)

            if volume_in_bracket <= 0:
                continue

            subtotal = (volume_in_bracket * bracket.price_per_m3).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            total += subtotal

            top = f"{bracket.max_m3}" if bracket.max_m3 else "∞"
            breakdown.append({
                'description': (
                    f'Escalão {bracket.min_m3}–{top} m³ '
                    f'({volume_in_bracket} m³ × R$ {bracket.price_per_m3}/m³)'
                ),
                'quantity': float(volume_in_bracket),
                'unit_price': float(bracket.price_per_m3),
                'subtotal': float(subtotal),
            })

            remaining -= volume_in_bracket

        return {'total_charge': total, 'breakdown': breakdown}


# ──────────────────────────────────────────────────────────────
# Geração de Faturas
# ──────────────────────────────────────────────────────────────

class InvoiceGenerationService:
    """
    Gera faturas mensais para todos os clientes ativos de uma empresa.
    Chamado via Celery (tarefa mensal) ou manualmente pela API.
    """

    @classmethod
    @transaction.atomic
    def generate_for_company(
        cls,
        company,
        reference_month: int,
        reference_year: int,
        due_day: int = 10,
    ) -> dict:
        """
        Gera faturas para todos os clientes ativos da empresa
        para o mês/ano de referência informado.

        Retorna resumo: {'created': N, 'skipped': N, 'errors': [...]}
        """
        from customers.models import Customer
        from meters.models import WaterMeter

        customers = Customer.objects.filter(
            company=company, is_active=True
        ).prefetch_related('addresses')

        results = {'created': 0, 'skipped': 0, 'errors': []}

        for customer in customers:
            try:
                invoice = cls._generate_customer_invoice(
                    company=company,
                    customer=customer,
                    reference_month=reference_month,
                    reference_year=reference_year,
                    due_day=due_day,
                )
                if invoice:
                    results['created'] += 1
                else:
                    results['skipped'] += 1
            except Exception as exc:
                logger.exception(
                    "Erro ao gerar fatura para cliente %s: %s", customer.pk, exc
                )
                results['errors'].append({
                    'customer_id': str(customer.pk),
                    'customer_name': f"{customer.first_name} {customer.last_name}",
                    'error': str(exc),
                })

        return results

    @classmethod
    def _generate_customer_invoice(
        cls,
        company,
        customer,
        reference_month: int,
        reference_year: int,
        due_day: int,
    ):
        from .models import Invoice, InvoiceItem, TariffPlan
        from meters.models import WaterMeter, MeterReading
        import calendar
        from datetime import date

        # Evita duplicata
        if Invoice.objects.filter(
            company=company,
            customer=customer,
            reference_month=reference_month,
            reference_year=reference_year,
        ).exists():
            logger.info(
                "Fatura já existe para cliente %s %d/%d",
                customer.pk, reference_month, reference_year
            )
            return None

        # Busca o medidor do cliente
        meter = (
            WaterMeter.objects
            .filter(address__customer=customer, company=company, status='ACTIVE')
            .first()
        )
        if not meter:
            logger.warning("Cliente %s sem medidor ativo.", customer.pk)
            return None

        # Consumo do período
        consumption_m3, reading_ids = cls._get_period_consumption(
            meter, reference_month, reference_year
        )

        # Plano tarifário vigente
        tariff = TariffPlan.objects.filter(
            company=company, is_active=True
        ).first()
        if not tariff:
            raise ValueError(f"Nenhum plano tarifário ativo para empresa {company.pk}")

        # Cálculo de valores
        calc = TariffCalculator.calculate_consumption_charge(tariff, consumption_m3)
        consumption_charge = calc['total_charge']
        base_fee = tariff.base_fee

        subtotal = base_fee + consumption_charge
        tax_amount = (subtotal * tariff.tax_rate).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        total = subtotal + tax_amount

        # Data de vencimento
        last_day = calendar.monthrange(reference_year, reference_month)[1]
        safe_day = min(due_day, last_day)
        due_date = date(reference_year, reference_month, safe_day)

        # Criar fatura
        invoice = Invoice.objects.create(
            company=company,
            customer=customer,
            tariff_plan=tariff,
            reference_month=reference_month,
            reference_year=reference_year,
            due_date=due_date,
            consumption_m3=consumption_m3,
            base_fee=base_fee,
            consumption_charge=consumption_charge,
            tax_amount=tax_amount,
            late_fee=Decimal('0'),
            total_amount=total,
            status='PENDING',
        )

        # Itens da fatura
        # 1. Taxa fixa
        InvoiceItem.objects.create(
            invoice=invoice,
            company=company,
            description='Taxa fixa mensal',
            quantity=Decimal('1'),
            unit_price=base_fee,
            subtotal=base_fee,
        )

        # 2. Escalões de consumo
        for item in calc['breakdown']:
            InvoiceItem.objects.create(
                invoice=invoice,
                company=company,
                description=item['description'],
                quantity=Decimal(str(item['quantity'])),
                unit_price=Decimal(str(item['unit_price'])),
                subtotal=Decimal(str(item['subtotal'])),
            )

        # 3. Imposto
        if tax_amount > 0:
            InvoiceItem.objects.create(
                invoice=invoice,
                company=company,
                description=f'Impostos ({tariff.tax_rate * 100:.2f}%)',
                quantity=Decimal('1'),
                unit_price=tax_amount,
                subtotal=tax_amount,
            )

        logger.info("Fatura %s criada para cliente %s.", invoice.pk, customer.pk)
        return invoice

    @staticmethod
    def _get_period_consumption(meter, month: int, year: int):
        """
        Retorna (consumption_m3, [reading_ids]) para o período mensal.
        Usa as leituras mais próximas do início e fim do mês.
        """
        from meters.models import MeterReading
        from datetime import date
        import calendar

        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        # Leitura mais próxima ao início do mês (ou antes)
        start_reading = (
            MeterReading.objects
            .filter(meter=meter, reading_date__date__lte=first_day)
            .order_by('-reading_date')
            .first()
        )

        # Leitura mais próxima ao fim do mês (ou dentro do mês)
        end_reading = (
            MeterReading.objects
            .filter(meter=meter, reading_date__date__lte=last_day)
            .order_by('-reading_date')
            .first()
        )

        if not end_reading or not start_reading:
            return Decimal('0'), []

        if start_reading.pk == end_reading.pk:
            return Decimal('0'), [str(start_reading.pk)]

        consumption = end_reading.reading_value - start_reading.reading_value
        return max(consumption, Decimal('0')), [
            str(start_reading.pk), str(end_reading.pk)
        ]


# ──────────────────────────────────────────────────────────────
# Aplicação de multas e juros por atraso
# ──────────────────────────────────────────────────────────────

class LateFeeService:
    """
    Aplica multas e juros às faturas vencidas.
    Executado diariamente via Celery beat.
    """

    @classmethod
    @transaction.atomic
    def apply_late_fees_for_company(cls, company) -> int:
        """
        Aplica multa e juros a todas as faturas PENDING vencidas.
        Retorna a quantidade de faturas atualizadas.
        """
        from .models import Invoice
        today = timezone.now().date()

        overdue_invoices = Invoice.objects.filter(
            company=company,
            status='PENDING',
            due_date__lt=today,
            tariff_plan__isnull=False,
        ).select_related('tariff_plan')

        updated = 0
        for invoice in overdue_invoices:
            cls._apply_to_invoice(invoice, today)
            updated += 1

        return updated

    @staticmethod
    def _apply_to_invoice(invoice, today):
        from .models import InvoiceItem
        tariff = invoice.tariff_plan
        days_overdue = (today - invoice.due_date).days

        base = invoice.base_fee + invoice.consumption_charge + invoice.tax_amount

        # Multa fixa (aplicada uma vez)
        late_fee = Decimal('0')
        if tariff.late_fee_rate > 0 and invoice.late_fee == 0:
            late_fee = (base * tariff.late_fee_rate).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

        # Juros diários compostos
        interest = Decimal('0')
        if tariff.daily_interest_rate > 0 and days_overdue > 0:
            factor = (1 + tariff.daily_interest_rate) ** days_overdue
            interest = (base * (Decimal(str(factor)) - 1)).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

        total_late = late_fee + interest
        if total_late <= invoice.late_fee:
            return  # já aplicado valor maior ou igual

        invoice.late_fee = total_late
        invoice.total_amount = (
            base + total_late
        )
        invoice.status = 'OVERDUE'
        invoice.save(update_fields=['late_fee', 'total_amount', 'status'])
