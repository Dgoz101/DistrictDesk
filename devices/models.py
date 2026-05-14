import uuid

from django.conf import settings
from django.db import models


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
    """Device record for inventory (FR-26–FR-29) plus warranty and public QR token."""
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
        'core.Location',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='devices',
    )
    purchase_date = models.DateField(null=True, blank=True)
    warranty_end_date = models.DateField(null=True, blank=True)
    purchase_vendor = models.CharField(max_length=200, blank=True)
    purchase_order = models.CharField(max_length=100, blank=True)
    public_report_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'devices_device'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['device_type']),
            models.Index(fields=['assigned_user']),
            models.Index(fields=['warranty_end_date']),
        ]

    def __str__(self):
        return f'{self.asset_tag} ({self.device_type.name})'


class DeviceCheckout(models.Model):
    """Loaner / checkout: who has the device and when (history of checkouts)."""
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='checkouts')
    checked_out_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='device_checkouts_held',
    )
    checked_out_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_checkouts_recorded',
    )

    class Meta:
        db_table = 'devices_devicecheckout'
        ordering = ['-checked_out_at']
        indexes = [
            models.Index(fields=['device', 'returned_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['device'],
                condition=models.Q(returned_at__isnull=True),
                name='devices_devicecheckout_one_open_per_device',
            ),
        ]

    def __str__(self):
        return f'{self.device_id} → {self.checked_out_to_id} @ {self.checked_out_at}'
