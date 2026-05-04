# apps/meters/serializers.py
from rest_framework import serializers
from apps.meters.models import WaterMeter, MeterReading
from apps.meters.services import MeterReadingService, ReadingValidationError
from .models import TariffPlan, TariffBracket, Invoice, InvoiceItem


from rest_framework import serializers

from .models import TariffPlan, Invoice, InvoiceItem




 

class InvoiceItemSerializer(serializers.ModelSerializer):

    class Meta:

        model = InvoiceItem

        fields = [

            'id', 'description', 'quantity',

            'unit_price', 'subtotal',

        ]

        read_only_fields = ['id', 'subtotal']



    def validate(self, data):

        # Calcula subtotal automaticamente

        data['subtotal'] = data['quantity'] * data['unit_price']

        return data





class InvoiceSerializer(serializers.ModelSerializer):

    items = InvoiceItemSerializer(many=True, read_only=True)

    customer_name = serializers.SerializerMethodField()

    is_overdue = serializers.SerializerMethodField()



    class Meta:

        model = Invoice

        fields = [

            'id', 'customer', 'customer_name',

            'due_date', 'total_amount', 'status',

            'is_overdue', 'pdf_file',

            'items', 'created_at', 'updated_at',

        ]

        read_only_fields = [

            'id', 'created_at', 'updated_at',

            'customer_name', 'is_overdue',

        ]



    def get_customer_name(self, obj):

        return f"{obj.customer.first_name} {obj.customer.last_name}"



    def get_is_overdue(self, obj):

        from django.utils import timezone

        if obj.status in ('PAID', 'CANCELLED'):

            return False

        return obj.due_date < timezone.now().date()



    def validate_customer(self, customer):

        """Garante que o cliente pertence à mesma empresa."""

        request = self.context.get('request')

        if request and not request.user.is_superuser:

            if customer.company != request.user.company:

                raise serializers.ValidationError(

                    "Este cliente não pertence à sua empresa."

                )

        return customer





class InvoiceListSerializer(serializers.ModelSerializer):

    customer_name = serializers.SerializerMethodField()



    class Meta:

        model = Invoice

        fields = [

            'id', 'customer_name', 'due_date',

            'total_amount', 'status',

        ]



    def get_customer_name(self, obj):

        return f"{obj.customer.first_name} {obj.customer.last_name}"





class InvoiceCreateWithItemsSerializer(serializers.ModelSerializer):

    """Cria Invoice + InvoiceItems em uma única requisição."""

    items = InvoiceItemSerializer(many=True)



    class Meta:

        model = Invoice

        fields = [

            'customer', 'due_date', 'total_amount',

            'status', 'items',

        ]



    def create(self, validated_data):

        items_data = validated_data.pop('items')

        invoice = Invoice.objects.create(**validated_data)

        for item_data in items_data:

            InvoiceItem.objects.create(

                invoice=invoice,

                company=invoice.company,

                **item_data

            )

        return invoice

class MeterReadingSerializer(serializers.ModelSerializer):
    reader_name = serializers.SerializerMethodField()
    consumption = serializers.SerializerMethodField()

    class Meta:
        model = MeterReading
        fields = [
            'id', 'meter', 'reader', 'reader_name',
            'reading_value', 'reading_date',
            'consumption',
            'anomaly_flag', 'anomaly_reason',
            'image_evidence', 'created_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'reader_name',
            'consumption', 'anomaly_flag', 'anomaly_reason',
        ]

    def get_reader_name(self, obj):
        return obj.reader.get_full_name() if obj.reader else None

    def get_consumption(self, obj):
        return MeterReadingService.calculate_consumption(obj)


class WaterMeterSerializer(serializers.ModelSerializer):
    address_detail = serializers.SerializerMethodField()
    last_reading = serializers.SerializerMethodField()
    consumption_history = serializers.SerializerMethodField()

    class Meta:
        model = WaterMeter
        fields = [
            'id', 'serial_number', 'address', 'address_detail',
            'installation_date', 'status',
            'last_reading', 'consumption_history',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'address_detail', 'last_reading', 'consumption_history',
        ]

    def get_address_detail(self, obj):
        from customers.serializers import AddressSerializer
        return AddressSerializer(obj.address).data

    def get_last_reading(self, obj):
        last = obj.readings.first()
        if not last:
            return None
        return {
            'id': str(last.id),
            'value': float(last.reading_value),
            'date': last.reading_date,
            'anomaly': last.anomaly_flag,
        }

    def get_consumption_history(self, obj):
        return MeterReadingService.get_meter_consumption_history(obj, limit=6)

    def validate_serial_number(self, value):
        qs = WaterMeter.objects.filter(serial_number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Já existe um medidor com este número de série."
            )
        return value


class WaterMeterListSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterMeter
        fields = ['id', 'serial_number', 'status', 'installation_date']

class TariffBracketSerializer(serializers.ModelSerializer):
    class Meta:
        model = TariffBracket
        fields = ['id', 'min_m3', 'max_m3', 'price_per_m3']
        read_only_fields = ['id']

    def validate(self, data):
        if data.get('max_m3') and data['max_m3'] <= data['min_m3']:
            raise serializers.ValidationError(
                "max_m3 deve ser maior que min_m3."
            )
        return data


class TariffPlanSerializer(serializers.ModelSerializer):
    brackets = TariffBracketSerializer(many=True, read_only=True)

    class Meta:
        model = TariffPlan
        fields = [
            'id', 'name', 'base_fee', 'cost_per_m3',
            'tax_rate', 'late_fee_rate', 'daily_interest_rate',
            'is_active', 'brackets',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
