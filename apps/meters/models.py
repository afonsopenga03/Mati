from django.db import models

# Create your models here.
# apps/meters/models.py
from core.models import TenantModel

class WaterMeter(TenantModel):
    STATUS_CHOICES = (('ACTIVE', 'Ativo'), ('INACTIVE', 'Inativo'), ('MAINTENANCE', 'Manutenção'))

    serial_number = models.CharField(max_length=50, unique=True)
    address = models.OneToOneField('customers.Address', on_delete=models.PROTECT)
    installation_date = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='ACTIVE')

class MeterReading(TenantModel):
    meter = models.ForeignKey(WaterMeter, on_delete=models.CASCADE, related_name='readings')
    reader = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    reading_value = models.DecimalField(max_digits=12, decimal_places=3) # m³
    reading_date = models.DateTimeField()
    image_evidence = models.ImageField(upload_to='readings/', null=True, blank=True)

    # --- ADICIONE ESTA LINHA ABAIXO ---
    anomaly_flag = models.BooleanField(default=False)
    # ----------------------------------

    class Meta:
        ordering = ['-reading_date']
