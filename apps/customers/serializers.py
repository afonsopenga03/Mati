# apps/customers/serializers.py
from rest_framework import serializers
from .models import Customer, Address


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id', 'street', 'number', 'neighborhood',
            'city', 'postal_code', 'latitude', 'longitude',
        ]
        read_only_fields = ['id']


class CustomerSerializer(serializers.ModelSerializer):
    addresses = AddressSerializer(many=True, read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'full_name',
            'email', 'document_id', 'is_active',
            'created_at', 'updated_at', 'addresses',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'full_name']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def validate_document_id(self, value):
        cleaned = ''.join(filter(str.isalnum, value))
        if len(cleaned) not in (11, 14):
            raise serializers.ValidationError(
                "document_id deve ter 11 (CPF) ou 14 (CNPJ) dígitos."
            )
        return cleaned

    def validate_email(self, value):
        # Garante unicidade de e-mail dentro da empresa
        request = self.context.get('request')
        qs = Customer.objects.filter(email=value)
        if request and hasattr(request.user, 'company') and request.user.company:
            qs = qs.filter(company=request.user.company)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Já existe um cliente com este e-mail nesta empresa."
            )
        return value


class CustomerListSerializer(serializers.ModelSerializer):
    """Versão leve para listagens."""
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['id', 'full_name', 'email', 'document_id', 'is_active']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
