from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'ADMIN'

class IsManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['ADMIN', 'MANAGER']

class IsFieldWorker(permissions.BasePermission):
    def has_permission(self, request, view):
        # Leituristas só podem acessar certos endpoints (como registrar leituras)
        return request.user.is_authenticated and request.user.role == 'READER'
