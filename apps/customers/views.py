# apps/customers/views.py
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.mixins import TenantQuerySetMixin
from core.permissions import IsManager, IsAdminUser
from core.pagination import StandardResultsPagination
from .models import Customer, Address
from apps.companies.models import Company
from .serializers import CustomerSerializer, CustomerListSerializer, AddressSerializer
from .filters import CustomerFilter

from subscriptions.decorators import check_limit
from subscriptions.services import SubscriptionService

class CustomerViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """
    CRUD completo de clientes com isolamento por empresa.
    - list / retrieve: Manager + Admin
    - create / update / destroy: Manager + Admin
    - Addresses são gerenciadas via endpoint aninhado
    """
    queryset = Customer.objects.prefetch_related('addresses').order_by('first_name')
    permission_classes = [IsManager]
    pagination_class = StandardResultsPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CustomerFilter
    search_fields = ['first_name', 'last_name', 'email', 'document_id']
    ordering_fields = ['first_name', 'last_name', 'created_at']
    ordering = ['first_name']

    def get_serializer_class(self):
        if self.action == 'list':
            return CustomerListSerializer
        return
    
    @check_limit('customers')
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        # Incrementa uso após criar com sucesso
        if response.status_code == 201:
            SubscriptionService.increment_usage(request.user.company, 'customers')
        return response
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        customer = self.get_object()
        customer.is_active = False
        customer.save(update_fields=['is_active'])
        return Response({'status': 'cliente desativado'})

    @action(detail=True, methods=['get', 'post'], url_path='addresses')
    def addresses(self, request, pk=None):
        customer = self.get_object()

        if request.method == 'GET':
            serializer = AddressSerializer(
                customer.addresses.all(), many=True
            )
            return Response(serializer.data)

        # POST — criar novo endereço
        serializer = AddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(customer=customer, company=customer.company)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
