# apps/subscriptions/decorators.py
from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from .services import SubscriptionService, SubscriptionLimitError


def check_limit(resource: str):
    """
    Decorator para views DRF que verifica limite antes de executar.

    Uso:
        @check_limit('customers')
        def create(self, request, *args, **kwargs):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            company = getattr(request.user, 'company', None)
            if company:
                try:
                    SubscriptionService.check_limit(company, resource)
                except SubscriptionLimitError as exc:
                    return Response(
                        {
                            'error': 'limit_exceeded',
                            'resource': exc.limit_type,
                            'message': str(exc),
                            'current': exc.current,
                            'limit': exc.limit,
                            'upgrade_url': '/api/subscriptions/plans/',
                        },
                        status=status.HTTP_402_PAYMENT_REQUIRED,
                    )
            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator
