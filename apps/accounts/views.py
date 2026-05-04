# apps/accounts/views.py
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from core.mixins import TenantQuerySetMixin
from core.permissions import IsAdminUser
from core.pagination import StandardResultsPagination
from apps.accounts.serializers import UserSerializer, UserCreateSerializer, ChangePasswordSerializer
from apps.companies.models import Company
from django.contrib.auth import get_user_model
User = get_user_model()


class UserViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """
    Admins gerenciam usuários da sua empresa.
    Cada usuário pode ver e editar seu próprio perfil via /me/.
    """
    queryset = User.objects.all().order_by('username')
    permission_classes = [IsAdminUser]
    pagination_class = StandardResultsPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['username', 'date_joined']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return User.objects.all().order_by('username')
        if user.company:
            return User.objects.filter(company=user.company).order_by('username')
        return User.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user = self.request.user
        company = None if user.is_superuser else user.company
        serializer.save(company=company)

    @action(
        detail=False, methods=['get', 'patch'],
        permission_classes=[IsAuthenticated],
        url_path='me'
    )
    def me(self, request):
        """Endpoint para o usuário ver/editar o próprio perfil."""
        if request.method == 'GET':
            serializer = UserSerializer(request.user)
            return Response(serializer.data)

        serializer = UserSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(
        detail=False, methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='change-password'
    )
    def change_password(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'status': 'senha alterada com sucesso'})
