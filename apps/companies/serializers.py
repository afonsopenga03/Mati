# apps/companies/serializers.py
from rest_framework import serializers
from .models import Company


class CompanySerializer(serializers.ModelSerializer):
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'tax_id', 'slug',
            'address', 'is_active', 'created_at',
            'employee_count',
        ]
        read_only_fields = ['id', 'created_at', 'employee_count']

    def get_employee_count(self, obj):
        return obj.employees.count()

    def validate_tax_id(self, value):
        # Remove pontuação antes de salvar (ex: "12.345.678/0001-99" → "12345678000199")
        cleaned = ''.join(filter(str.isalnum, value))
        if len(cleaned) not in (11, 14):
            raise serializers.ValidationError(
                "tax_id deve conter 11 (CPF) ou 14 (CNPJ) dígitos."
            )
        return cleaned


class CompanyListSerializer(serializers.ModelSerializer):
    """Versão leve para listagens."""
    class Meta:
        model = Company
        fields = ['id', 'name', 'slug', 'is_active']
