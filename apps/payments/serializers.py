# apps/payments/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import Payment
from apps.billing.models import Invoice


class PaymentSerializer(serializers.ModelSerializer):
    invoice_info = serializers.SerializerMethodField()
    registered_by_name = serializers.SerializerMethodField()
    payment_summary = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'invoice', 'invoice_info',
            'payment_date', 'amount_paid',
            'method', 'status',
            'transaction_id', 'reference_note',
            'registered_by', 'registered_by_name',
            'reversed_at', 'reversal_reason',
            'payment_summary',
            'created_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'status',
            'invoice_info', 'registered_by_name',
            'reversed_at', 'reversal_reason',
            'payment_summary',
        ]

    def get_invoice_info(self, obj):
        inv = obj.invoice
        return {
            'id': str(inv.id),
            'customer': f"{inv.customer.first_name} {inv.customer.last_name}",
            'total_amount': float(inv.total_amount),
            'status': inv.status,
            'reference': f"{inv.reference_month:02d}/{inv.reference_year}",
        }

    def get_registered_by_name(self, obj):
        return obj.registered_by.get_full_name() if obj.registered_by else None

    def get_payment_summary(self, obj):
        from .services import PaymentService
        return PaymentService.get_invoice_payment_summary(obj.invoice)

    def validate_invoice(self, invoice):
        request = self.context.get('request')
        if request and not request.user.is_superuser:
            if invoice.company != request.user.company:
                raise serializers.ValidationError(
                    "Esta fatura não pertence à sua empresa."
                )
        if invoice.status == 'CANCELLED':
            raise serializers.ValidationError(
                "Não é possível pagar uma fatura cancelada."
            )
        return invoice

    def validate_payment_date(self, value):
        if value > timezone.now():
            raise serializers.ValidationError(
                "Data de pagamento não pode ser futura."
            )
        return value

    def validate_amount_paid(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "O valor pago deve ser maior que zero."
            )
        return value


class PaymentListSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()
    method_display = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'customer_name', 'amount_paid',
            'method', 'method_display', 'status',
            'payment_date', 'transaction_id',
        ]

    def get_customer_name(self, obj):
        c = obj.invoice.customer
        return f"{c.first_name} {c.last_name}"

    def get_method_display(self, obj):
        return obj.get_method_display()


class ReversalSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=10, max_length=500)
