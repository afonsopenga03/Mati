# apps/subscriptions/middleware.py
from django.http import JsonResponse
from .services import SubscriptionService


# Endpoints que NÃO passam pela verificação de subscrição
EXEMPT_PATHS = {
    '/api/auth/',
    '/api/subscriptions/',
    '/admin/',
    '/dashboard/',
}


class SubscriptionMiddleware:
    """
    Middleware que bloqueia a API se a subscrição estiver inactiva/expirada.
    Inserido após AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._should_check(request):
            response = self._check_subscription(request)
            if response:
                return response
        return self.get_response(request)

    def _should_check(self, request) -> bool:
        if not request.path.startswith('/api/'):
            return False
        for exempt in EXEMPT_PATHS:
            if request.path.startswith(exempt):
                return False
        user = getattr(request, 'user', None)
        return user and user.is_authenticated and not user.is_superuser

    def _check_subscription(self, request):
        user = request.user
        company = getattr(user, 'company', None)
        if not company:
            return None

        try:
            sub = company.subscription
        except Exception:
            return JsonResponse({
                'error': 'subscription_required',
                'message': 'Esta empresa não possui subscrição activa.',
                'upgrade_url': '/api/subscriptions/plans/',
            }, status=402)

        # Verifica e expira se necessário
        SubscriptionService.check_and_expire(sub)

        if not sub.is_active:
            return JsonResponse({
                'error': 'subscription_inactive',
                'status': sub.status,
                'message': (
                    f'Subscrição {sub.get_status_display().lower()}. '
                    'Renove para continuar utilizando o sistema.'
                ),
                'days_overdue': abs(sub.days_remaining),
                'upgrade_url': '/api/subscriptions/plans/',
            }, status=402)

        return None
