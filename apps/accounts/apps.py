from django.apps import AppConfig


# apps/accounts/apps.py
class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'  # Mantenha apenas o nome do app, o sys.path resolve o resto.
