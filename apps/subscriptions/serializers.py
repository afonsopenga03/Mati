# apps/subscriptions/serializers.py
from rest_framework import serializers
from .models import Plan, Subscription, SubscriptionInvoice


class PlanSerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = [
            'id', 'tier', 'name', 'description',
            'price_monthly', 'price_yearly',
            'max_customers', 'max_meters', 'max_users',
            'max_readings_per_month', 'max_invoices_per_month',
            'trial_days', 'features',
        ]

    def get_features(self, obj):
        return {
            'api_access':       obj.has_api_access,
            'field_app':        obj.has_field_app,
            'reports':          obj.has_reports,
            'multi_user':       obj.has_multi_user,
            'custom_branding':  obj.has_custom_branding,
            'priority_support': obj.has_priority_support,
            'data_export':      obj.has_data_export,
        }


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    is_in_trial = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            'id', 'company', 'company_name',
            'plan', 'plan_name', 'status', 'billing_cycle',
            'started_at', 'trial_ends_at',
            'current_period_start', 'current_period_end',
            'days_remaining', 'is_in_trial',
            'cancelled_at',
        ]
        read_only_fields = fields

    def get_plan_name(self, obj):
        return obj.plan.name

    def get_days_remaining(self, obj):
        return obj.days_remaining

    def get_is_in_trial(self, obj):
        return obj.is_in_trial

    def get_company_name(self, obj):
        return obj.company.name


class SubscriptionInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionInvoice
        fields = [
            'id', 'amount', 'status',
            'period_start', 'period_end',
            'paid_at', 'payment_method', 'transaction_ref',
            'created_at',
        ]
        read_only_fields = fields


class ChangePlanSerializer(serializers.Serializer):
    plan = serializers.PrimaryKeyRelatedField(
        queryset=Plan.objects.filter(is_active=True)
    )
    billing_cycle = serializers.ChoiceField(
        choices=['MONTHLY', 'YEARLY'], required=False
    )


class SubscriptionInvoicePaySerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(
        choices=['MPESA', 'EMOLA', 'BANK_TRANSFER', 'CASH']
    )
    transaction_ref = serializers.CharField(max_length=255, required=False)
