# apps/fieldwork/serializers.py
from rest_framework import serializers
from .models import Route, RouteStop, FieldTask, OfflineSyncLog


class RouteStopSerializer(serializers.ModelSerializer):
    meter_serial = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()

    class Meta:
        model = RouteStop
        fields = [
            'id', 'order', 'meter', 'meter_serial',
            'customer_name', 'address', 'notes',
        ]
        read_only_fields = ['id', 'meter_serial', 'customer_name', 'address']

    def get_meter_serial(self, obj):
        return obj.meter.serial_number

    def get_customer_name(self, obj):
        c = obj.meter.address.customer
        return f"{c.first_name} {c.last_name}"

    def get_address(self, obj):
        a = obj.meter.address
        return {
            'street': a.street, 'number': a.number,
            'city': a.city, 'postal_code': a.postal_code,
            'latitude': float(a.latitude) if a.latitude else None,
            'longitude': float(a.longitude) if a.longitude else None,
        }


class RouteSerializer(serializers.ModelSerializer):
    stops = RouteStopSerializer(many=True, read_only=True)
    stop_count = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = [
            'id', 'name', 'description',
            'assigned_to', 'assigned_to_name',
            'is_active', 'stop_count', 'stops',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'stop_count', 'assigned_to_name']

    def get_stop_count(self, obj):
        return obj.stops.count()

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() if obj.assigned_to else None


class RouteListSerializer(serializers.ModelSerializer):
    stop_count = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = ['id', 'name', 'assigned_to_name', 'stop_count', 'is_active']

    def get_stop_count(self, obj):
        return obj.stops.count()

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() if obj.assigned_to else None


class FieldTaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.SerializerMethodField()
    meter_serial = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = FieldTask
        fields = [
            'id', 'client_uuid', 'task_type', 'status', 'priority',
            'assigned_to', 'assigned_to_name',
            'meter', 'meter_serial', 'customer_name',
            'route', 'title', 'description',
            'scheduled_date', 'due_date',
            'completed_at', 'result_notes', 'result_image',
            'gps_latitude', 'gps_longitude',
            'order_in_route', 'synced_at', 'device_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'assigned_to_name', 'meter_serial', 'customer_name',
            'synced_at',
        ]

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name()

    def get_meter_serial(self, obj):
        return obj.meter.serial_number if obj.meter else None

    def get_customer_name(self, obj):
        if obj.meter:
            c = obj.meter.address.customer
            return f"{c.first_name} {c.last_name}"
        return None


class FieldTaskCompleteSerializer(serializers.Serializer):
    """Payload para concluir tarefa diretamente pela API."""
    result_notes = serializers.CharField(required=False, allow_blank=True)
    gps_latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    gps_longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    result_image = serializers.ImageField(required=False, allow_null=True)


class OfflineSyncSerializer(serializers.Serializer):
    """Payload completo de sincronização offline."""
    device_id = serializers.CharField(max_length=100)
    tasks = serializers.ListField(child=serializers.DictField(), default=list)
    readings = serializers.ListField(child=serializers.DictField(), default=list)

    def validate_readings(self, readings):
        for r in readings:
            if 'meter_id' not in r:
                raise serializers.ValidationError("Cada leitura precisa de meter_id.")
            if 'reading_value' not in r:
                raise serializers.ValidationError("Cada leitura precisa de reading_value.")
        return readings
