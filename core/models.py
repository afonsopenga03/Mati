# apps/core/models.py
from django.db import models
import uuid

class TenantModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Importante usar a string 'companies.Company' aqui também!
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE, related_name="%(class)s_related")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
