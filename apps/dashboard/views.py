# apps/dashboard/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, date
import json


@login_required
def dashboard(request):
    company = request.user.company
    today = timezone.now().date()
    this_month = today.replace(day=1)

    # ── Clientes ──────────────────────────────
    from apps.customers.models import Customer
    total_customers = Customer.objects.filter(company=company, is_active=True).count()
    new_customers_month = Customer.objects.filter(
        company=company,
        created_at__date__gte=this_month
    ).count()

    # ── Medidores ─────────────────────────────
    from apps.meters.models import WaterMeter, MeterReading
    total_meters = WaterMeter.objects.filter(company=company).count()
    active_meters = WaterMeter.objects.filter(company=company, status='ACTIVE').count()
    maintenance_meters = WaterMeter.objects.filter(company=company, status='MAINTENANCE').count()

    # ── Faturas ───────────────────────────────
    from apps.billing.models import Invoice
    invoices_qs = Invoice.objects.filter(company=company)

    pending_invoices = invoices_qs.filter(status='PENDING').aggregate(
        count=Count('id'), total=Sum('total_amount')
    )
    overdue_invoices = invoices_qs.filter(status='OVERDUE').aggregate(
        count=Count('id'), total=Sum('total_amount')
    )
    paid_this_month = invoices_qs.filter(
        status='PAID',
        reference_month=today.month,
        reference_year=today.year,
    ).aggregate(count=Count('id'), total=Sum('total_amount'))

    # ── Receita (últimos 6 meses) ─────────────
    revenue_labels = []
    revenue_data = []
    for i in range(5, -1, -1):
        d = today - timedelta(days=i * 30)
        label = d.strftime('%b/%y')
        total = invoices_qs.filter(
            status='PAID',
            reference_month=d.month,
            reference_year=d.year,
        ).aggregate(t=Sum('total_amount'))['t'] or 0
        revenue_labels.append(label)
        revenue_data.append(float(total))

    # ── Pagamentos ────────────────────────────
    from apps.payments.models import Payment
    payments_qs = Payment.objects.filter(company=company, status='CONFIRMED')
    total_received = payments_qs.aggregate(t=Sum('amount_paid'))['t'] or 0

    payments_by_method = list(
        payments_qs.values('method')
        .annotate(total=Sum('amount_paid'), count=Count('id'))
        .order_by('-total')
    )

    # ── Consumo mensal (últimos 6 meses) ──────
    consumption_labels = []
    consumption_data = []
    for i in range(5, -1, -1):
        d = today - timedelta(days=i * 30)
        total_m3 = invoices_qs.filter(
            reference_month=d.month,
            reference_year=d.year,
        ).aggregate(t=Sum('consumption_m3'))['t'] or 0
        consumption_labels.append(d.strftime('%b/%y'))
        consumption_data.append(float(total_m3))

    # ── Leituras recentes ─────────────────────
    recent_readings = (
        MeterReading.objects
        .filter(company=company)
        .select_related('meter', 'reader')
        .order_by('-reading_date')[:10]
    )

    # ── Anomalias pendentes ───────────────────
    anomalies_count = MeterReading.objects.filter(
        company=company, anomaly_flag=True,
        reading_date__date__gte=today - timedelta(days=30),
    ).count()

    # ── Faturas recentes ──────────────────────
    recent_invoices = (
        invoices_qs
        .select_related('customer')
        .order_by('-created_at')[:8]
    )

    # ── Faturas vencendo em 7 dias ────────────
    soon_due = invoices_qs.filter(
        status='PENDING',
        due_date__range=[today, today + timedelta(days=7)],
    ).select_related('customer').order_by('due_date')[:5]

    context = {
        'user': request.user,
        'company': company,
        'today': today,

        # KPIs
        'total_customers': total_customers,
        'new_customers_month': new_customers_month,
        'total_meters': total_meters,
        'active_meters': active_meters,
        'maintenance_meters': maintenance_meters,
        'total_received': total_received,
        'anomalies_count': anomalies_count,

        # Faturas
        'pending_count': pending_invoices['count'],
        'pending_total': pending_invoices['total'] or 0,
        'overdue_count': overdue_invoices['count'],
        'overdue_total': overdue_invoices['total'] or 0,
        'paid_month_count': paid_this_month['count'],
        'paid_month_total': paid_this_month['total'] or 0,

        # Pagamentos por método
        'payments_by_method': payments_by_method,

        # Gráficos (JSON para Chart.js)
        'revenue_labels': json.dumps(revenue_labels),
        'revenue_data': json.dumps(revenue_data),
        'consumption_labels': json.dumps(consumption_labels),
        'consumption_data': json.dumps(consumption_data),

        # Tabelas
        'recent_readings': recent_readings,
        'recent_invoices': recent_invoices,
        'soon_due': soon_due,
    }

    return render(request, 'dashboard/index.html', context)
