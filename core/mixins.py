# apps/core/mixins.py
from rest_framework.exceptions import PermissionDenied


class TenantQuerySetMixin:
    """
    Garante que cada usuário só enxerga e cria dados da sua própria empresa.
    Superusers Django têm acesso irrestrito (útil para suporte/admin).
    """

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if user.is_superuser:
            return qs

        if not hasattr(user, 'company') or user.company is None:
            # Usuário sem empresa não vê nada — retorna queryset vazio
            return qs.none()

        return qs.filter(company=user.company)

    def perform_create(self, serializer):
        user = self.request.user

        if user.is_superuser:
            # Superuser pode passar company explicitamente no payload
            serializer.save()
            return

        if not hasattr(user, 'company') or user.company is None:
            raise PermissionDenied(
                "Seu usuário não está associado a nenhuma empresa."
            )

        serializer.save(company=user.company)

    def perform_update(self, serializer):
        """
        Evita que alguém troque o campo company via PATCH/PUT.
        """
        serializer.save()
