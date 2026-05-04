# apps/meters/apps.py
from django.apps import AppConfig

class MetersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.meters'  # <-- PRECISA ser 'apps.meters', não apenas 'meters'
