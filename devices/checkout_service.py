"""Loaner checkout: at most one open checkout per device (DB constraint + status hints)."""
from datetime import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Device, DeviceCheckout, DeviceStatus


def _status_by_name(name: str) -> DeviceStatus | None:
    return DeviceStatus.objects.filter(name__iexact=name).first()


@transaction.atomic
def checkout_device(
    *,
    device: Device,
    checked_out_to,
    due_at: datetime | None = None,
    notes: str = '',
    created_by=None,
) -> DeviceCheckout:
    """Create an open checkout. Raises IntegrityError if device already has an open checkout."""
    co = DeviceCheckout.objects.create(
        device=device,
        checked_out_to=checked_out_to,
        due_at=due_at,
        notes=notes or '',
        created_by=created_by,
    )
    st = _status_by_name('Checked-out')
    if st is not None:
        device.status = st
        device.save(update_fields=['status', 'updated_at'])
    return co


@transaction.atomic
def return_open_checkout(*, device: Device) -> DeviceCheckout | None:
    """Set returned_at on the open checkout for this device, if any. Sync status to In-service when present."""
    open_co = (
        DeviceCheckout.objects.select_for_update()
        .filter(device=device, returned_at__isnull=True)
        .order_by('-checked_out_at')
        .first()
    )
    if open_co is None:
        return None
    open_co.returned_at = timezone.now()
    open_co.save(update_fields=['returned_at'])
    st = _status_by_name('In-service')
    if st is not None:
        device.status = st
        device.save(update_fields=['status', 'updated_at'])
    return open_co


def try_checkout(*args, **kwargs):
    """Like checkout_device but wraps IntegrityError as None return for UX (optional)."""
    try:
        return checkout_device(*args, **kwargs), None
    except IntegrityError:
        return None, 'This device already has an open checkout.'
