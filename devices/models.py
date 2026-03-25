from django.conf import settings
from django.db import models

from core.models import Location


class DeviceType(models.Model):
    """Lookup: Laptop, Printer, etc. (FR-26)."""
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'devices_devicetype'

    def __str__(self):
        return self.name


class DeviceStatus(models.Model):
    """Lookup: In-service, Checked-out, Repair, Retired (FR-28)."""
    name = models.CharField(max_length=50)

    class Meta:
        db_table = 'devices_devicestatus'

    def __str__(self):
        return self.name


class Device(models.Model):
    """Device record for inventory (FR-26–FR-29)."""
    asset_tag = models.CharField(max_length=50, unique=True)
    device_type = models.ForeignKey(DeviceType, on_delete=models.PROTECT, related_name='devices')
    model = models.CharField(max_length=150, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    status = models.ForeignKey(DeviceStatus, on_delete=models.PROTECT, related_name='devices')
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_devices',
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devices',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'devices_device'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['device_type']),
            models.Index(fields=['assigned_user']),
        ]

    def __str__(self):
        return f'{self.asset_tag} ({self.device_type.name})'
