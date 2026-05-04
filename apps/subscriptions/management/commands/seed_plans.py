# subscriptions/management/commands/seed_plans.py
from django.core.management.base import BaseCommand
from subscriptions.models import Plan

class Command(BaseCommand):
    help = 'Cria os planos SaaS padrão'

    def handle(self, *args, **options):
        plans = [
            dict(
                tier='TRIAL', name='Trial Grátis',
                description='14 dias grátis, sem cartão de crédito.',
                price_monthly=0, trial_days=14,
                max_customers=50, max_meters=50, max_users=3,
                max_readings_per_month=200, max_invoices_per_month=50,
                has_api_access=True, has_field_app=False,
                has_reports=False, has_multi_user=False,
            ),
            dict(
                tier='BASIC', name='Básico',
                description='Para pequenas distribuidoras.',
                price_monthly=1500, price_yearly=15000, trial_days=14,
                max_customers=500, max_meters=500, max_users=5,
                max_readings_per_month=2000, max_invoices_per_month=500,
                has_api_access=True, has_field_app=False,
                has_reports=True, has_multi_user=True,
                has_data_export=True,
            ),
            dict(
                tier='PRO', name='Profissional',
                description='Para distribuidoras de médio porte.',
                price_monthly=4500, price_yearly=45000, trial_days=14,
                max_customers=5000, max_meters=5000, max_users=20,
                max_readings_per_month=0, max_invoices_per_month=0,
                has_api_access=True, has_field_app=True,
                has_reports=True, has_multi_user=True,
                has_custom_branding=True, has_data_export=True,
                has_priority_support=True,
            ),
            dict(
                tier='ENTERPRISE', name='Enterprise',
                description='Sem limites. SLA garantido.',
                price_monthly=12000, price_yearly=120000, trial_days=30,
                max_customers=0, max_meters=0, max_users=0,
                max_readings_per_month=0, max_invoices_per_month=0,
                has_api_access=True, has_field_app=True,
                has_reports=True, has_multi_user=True,
                has_custom_branding=True, has_data_export=True,
                has_priority_support=True,
            ),
        ]

        for data in plans:
            Plan.objects.update_or_create(tier=data['tier'], defaults=data)
            self.stdout.write(f"  ✓ Plano {data['name']} criado/actualizado.")

        self.stdout.write(self.style.SUCCESS('Planos criados com sucesso!'))
