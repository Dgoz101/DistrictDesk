import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
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

    @property
    def fine_total(self) -> Decimal:
        total = Decimal('0.00')
        for fine in self.fines.exclude(status=DeviceFine.Status.WAIVED):
            total += fine.line_total
        return total


class DeviceCheckoutPolicy(models.Model):
    """Singleton-style district settings for loaner late fees (admin-configurable)."""

    late_fee_enabled = models.BooleanField(default=True)
    late_fee_per_day = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('5.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    late_grace_days = models.PositiveSmallIntegerField(
        default=0,
        help_text='Days after due date before late fees begin.',
    )
    late_fee_max_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Optional cap per checkout; leave blank for no cap.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'devices_devicecheckoutpolicy'
        verbose_name_plural = 'Device checkout policies'

    def __str__(self):
        return 'Checkout policy'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class DeviceFineType(models.Model):
    """Configurable damage / fee catalog (Chromebook-oriented defaults seeded)."""

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    default_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(
        default=False,
        help_text='System types cannot be deleted (e.g. late return).',
    )

    class Meta:
        db_table = 'devices_devicefinetype'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class DeviceFine(models.Model):
    """Fine assessed on a completed checkout (damage, late return, etc.)."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        WAIVED = 'waived', 'Waived'

    checkout = models.ForeignKey(DeviceCheckout, on_delete=models.CASCADE, related_name='fines')
    fine_type = models.ForeignKey(
        DeviceFineType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fines',
    )
    description = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    quantity = models.PositiveSmallIntegerField(default=1)
    is_late_fee = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    notes = models.TextField(blank=True)
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='device_fines_assessed',
    )
    assessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'devices_devicefine'
        ordering = ['-assessed_at']
        indexes = [
            models.Index(fields=['checkout', 'status']),
            models.Index(fields=['status', 'assessed_at']),
        ]

    def __str__(self):
        return f'{self.description} (${self.line_total})'

    @property
    def line_total(self) -> Decimal:
        return (self.amount * self.quantity).quantize(Decimal('0.01'))
