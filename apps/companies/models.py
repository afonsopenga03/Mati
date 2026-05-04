from django.db import models

# Create your models here.
# apps/companies/models.

class Company(models.Model):
    name = models.CharField(max_length=255)
    tax_id = models.CharField(max_length=20, unique=True) # CNPJ/NIF
    slug = models.SlugField(unique=True)
    address = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
