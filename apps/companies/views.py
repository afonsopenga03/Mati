# apps/companies/views.py
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsAdminUser
from core.pagination import StandardResultsPagination
from .models import Company
from .serializers import CompanySerializer, CompanyListSerializer


class CompanyViewSet(viewsets.ModelViewSet):
    """
    CRUD de empresas. Acessível apenas por superusers e admins globais.
    Admins de tenant só enxergam a própria empresa.
    """
    queryset = Company.objects.all().order_by('name')
    permission_classes = [IsAdminUser]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'tax_id', 'slug']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return CompanyListSerializer
        return CompanySerializer

    def get_queryset(self):
        user = self.request.user
        # Superuser vê tudo; admin de tenant vê só a própria empresa
        if user.is_superuser:
            return Company.objects.all().order_by('name')
        if user.company:
            return Company.objects.filter(pk=user.company.pk)
        return Company.objects.none()

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        company = self.get_object()
        company.is_active = False
        company.save(update_fields=['is_active'])
        return Response({'status': 'empresa desativada'})

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        company = self.get_object()
        company.is_active = True
        company.save(update_fields=['is_active'])
        return Response({'status': 'empresa ativada'})
