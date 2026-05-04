# No core/urls.py, adicionar:
from fieldwork.views import RouteViewSet, FieldTaskViewSet

router.register(r'routes',      RouteViewSet,     basename='route')
router.register(r'field-tasks', FieldTaskViewSet, basename='fieldtask')
