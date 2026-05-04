# core/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from apps.accounts.views import UserViewSet
from apps.companies.views import CompanyViewSet
from apps.customers.views import CustomerViewSet
from apps.meters.views import WaterMeterViewSet
from apps.billing.views import TariffPlanViewSet, InvoiceViewSet
from apps.payments.views import PaymentViewSet
from apps.subscriptions.views import PlanViewSet, SubscriptionViewSet
router = DefaultRouter()
router.register(r'users',      UserViewSet,       basename='user')
router.register(r'companies',  CompanyViewSet,    basename='company')
router.register(r'customers',  CustomerViewSet,   basename='customer')
router.register(r'meters',     WaterMeterViewSet, basename='meter')
router.register(r'tariffs',    TariffPlanViewSet, basename='tariff')
router.register(r'invoices',   InvoiceViewSet,    basename='invoice')
router.register(r'payments',   PaymentViewSet,    basename='payment')
router.register(r'subscriptions/plans', PlanViewSet, basename='plan')
router.register(r'subscriptions',       SubscriptionViewSet, basename='subscription')

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT
    path('api/auth/login/',   TokenObtainPairView.as_view(), name='token_obtain'),
    path('api/auth/refresh/', TokenRefreshView.as_view(),   name='token_refresh'),
    path('api/auth/verify/',  TokenVerifyView.as_view(),    name='token_verify'),

    # API
    path('api/', include(router.urls)),
    path('api/payments/<uuid:invoice_pk>/history/', PaymentViewSet.as_view({'get': 'by_invoice'})),
    path('dashboard/', include('dashboard.urls')),
]
