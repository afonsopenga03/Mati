from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Administrador'),
        ('CLERK', 'Atendente'),
        ('READER', 'Leiturista'),
        ('CUSTOMER', 'Cliente'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='CLERK')

    # Usamos a string 'app_label.ModelName' para evitar o NameError e Circular Imports
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='employees'
    )
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
