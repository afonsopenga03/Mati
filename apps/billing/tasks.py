# apps/billing/tasks.py
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def generate_monthly_invoices(self, company_id: str = None):
    """
    Gera faturas mensais. Executada no 1º dia de cada mês.
    Se company_id for None, processa TODAS as empresas ativas.
    """
    from companies.models import Company
    from billing.services import InvoiceGenerationService

    today = timezone.now().date()
    # O período de referência é o mês ANTERIOR
    if today.month == 1:
        ref_month, ref_year = 12, today.year - 1
    else:
        ref_month, ref_year = today.month - 1, today.year

    companies = (
        Company.objects.filter(pk=company_id)
        if company_id
        else Company.objects.filter(is_active=True)
    )

    total_summary = {'created': 0, 'skipped': 0, 'errors': []}

    for company in companies:
        try:
            result = InvoiceGenerationService.generate_for_company(
                company=company,
                reference_month=ref_month,
                reference_year=ref_year,
            )
            total_summary['created'] += result['created']
            total_summary['skipped'] += result['skipped']
            total_summary['errors'].extend(result['errors'])
            logger.info(
                "Empresa %s: %d faturas criadas, %d ignoradas.",
                company.pk, result['created'], result['skipped']
            )
        except Exception as exc:
            logger.exception("Erro ao processar empresa %s: %s", company.pk, exc)
            self.retry(exc=exc)

    return total_summary


@shared_task(bind=True, max_retries=3)
def apply_late_fees(self):
    """
    Aplica multas/juros a faturas vencidas. Executada diariamente.
    """
    from companies.models import Company
    from billing.services import LateFeeService

    updated_total = 0
    for company in Company.objects.filter(is_active=True):
        try:
            count = LateFeeService.apply_late_fees_for_company(company)
            updated_total += count
        except Exception as exc:
            logger.exception("Erro ao aplicar multas empresa %s: %s", company.pk, exc)
            self.retry(exc=exc)

    logger.info("Multas aplicadas em %d faturas.", updated_total)
    return {'invoices_updated': updated_total}
