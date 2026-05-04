# apps/meters/serializers.py
from rest_framework import serializers
from .models import WaterMeter, MeterReading
from .services import MeterReadingService, ReadingValidationError


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
