"""Checkout return fines: damage catalog, late fees, waive/paid."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from .models import Device, DeviceCheckout, DeviceCheckoutPolicy, DeviceFine, DeviceFineType, DeviceStatus


@dataclass
class LateFeePreview:
    days_late: int
    amount: Decimal
    due_at_display: str


@dataclass
class FineLineInput:
    fine_type_id: int | None
    description: str
    amount: Decimal
    quantity: int
    is_late_fee: bool = False
    notes: str = ''


def calculate_late_fee(checkout: DeviceCheckout, policy: DeviceCheckoutPolicy | None = None, *, at=None) -> LateFeePreview | None:
    policy = policy or DeviceCheckoutPolicy.get_solo()
    if not policy.late_fee_enabled or not checkout.due_at:
        return None
    at = at or timezone.now()
    if timezone.is_naive(at):
        at = timezone.make_aware(at)
    due = checkout.due_at
    if timezone.is_naive(due):
        due = timezone.make_aware(due)
    if at <= due:
        return None
    due_date = timezone.localtime(due).date()
    return_date = timezone.localtime(at).date()
    days_late = (return_date - due_date).days - policy.late_grace_days
    if days_late <= 0:
        return None
    amount = (Decimal(days_late) * policy.late_fee_per_day).quantize(Decimal('0.01'))
    if policy.late_fee_max_amount is not None:
        amount = min(amount, policy.late_fee_max_amount)
    return LateFeePreview(
        days_late=days_late,
        amount=amount,
        due_at_display=timezone.localtime(due).strftime('%Y-%m-%d %H:%M'),
    )


def _status_by_name(name: str) -> DeviceStatus | None:
    return DeviceStatus.objects.filter(name__iexact=name).first()


@transaction.atomic
def return_checkout_with_fines(
    *,
    device: Device,
    actor,
    fine_lines: list[FineLineInput],
    set_repair_status: bool = False,
) -> DeviceCheckout | None:
    """Close open checkout and persist fine line items."""
    open_co = (
        DeviceCheckout.objects.select_for_update()
        .filter(device=device, returned_at__isnull=True)
        .order_by('-checked_out_at')
        .first()
    )
    if open_co is None:
        return None

    returned_at = timezone.now()
    open_co.returned_at = returned_at
    open_co.save(update_fields=['returned_at'])

    for line in fine_lines:
        if line.amount < 0 or line.quantity < 1:
            continue
        DeviceFine.objects.create(
            checkout=open_co,
            fine_type_id=line.fine_type_id,
            description=line.description[:200],
            amount=line.amount,
            quantity=line.quantity,
            is_late_fee=line.is_late_fee,
            notes=line.notes or '',
            assessed_by=actor,
        )

    st = _status_by_name('In-service')
    if set_repair_status:
        repair = _status_by_name('Repair')
        if repair is not None:
            device.status = repair
        elif st is not None:
            device.status = st
    elif st is not None:
        device.status = st
    device.save(update_fields=['status', 'updated_at'])
    return open_co


def parse_fine_lines_from_post(post, *, late_preview: LateFeePreview | None) -> list[FineLineInput]:
    """Build fine lines from return-inspection POST data."""
    lines: list[FineLineInput] = []
    assess = post.get('assess_fines') == '1' or post.get('condition') == 'assess'

    if post.get('apply_late_fee') == '1' and late_preview is not None:
        raw_amount = post.get('late_fee_amount', '').strip()
        try:
            amount = Decimal(raw_amount) if raw_amount else late_preview.amount
        except Exception:
            amount = late_preview.amount
        late_type = DeviceFineType.objects.filter(code='late_return').first()
        lines.append(
            FineLineInput(
                fine_type_id=late_type.pk if late_type else None,
                description=f'Late return ({late_preview.days_late} day{"s" if late_preview.days_late != 1 else ""})',
                amount=amount,
                quantity=1,
                is_late_fee=True,
            )
        )

    if not assess:
        return lines

    selected = post.getlist('fine_type')
    for sid in selected:
        try:
            ft_id = int(sid)
        except (ValueError, TypeError):
            continue
        ft = DeviceFineType.objects.filter(pk=ft_id, is_active=True).first()
        if not ft:
            continue
        qty_raw = post.get(f'fine_qty_{ft_id}', '1').strip() or '1'
        amt_raw = post.get(f'fine_amount_{ft_id}', '').strip()
        try:
            quantity = max(1, int(qty_raw))
        except (ValueError, TypeError):
            quantity = 1
        try:
            amount = Decimal(amt_raw) if amt_raw else ft.default_amount
        except Exception:
            amount = ft.default_amount
        note = (post.get(f'fine_notes_{ft_id}', '') or '').strip()
        lines.append(
            FineLineInput(
                fine_type_id=ft.pk,
                description=ft.name,
                amount=amount,
                quantity=quantity,
                notes=note,
            )
        )

    custom_desc = (post.get('custom_fine_description') or '').strip()
    custom_amt = (post.get('custom_fine_amount') or '').strip()
    if custom_desc and custom_amt:
        try:
            amount = Decimal(custom_amt)
            if amount > 0:
                lines.append(
                    FineLineInput(
                        fine_type_id=None,
                        description=custom_desc[:200],
                        amount=amount,
                        quantity=1,
                        notes=(post.get('custom_fine_notes') or '').strip(),
                    )
                )
        except Exception:
            pass

    return lines


@transaction.atomic
def add_fines_to_checkout(*, checkout: DeviceCheckout, actor, fine_lines: list[FineLineInput]) -> int:
    if checkout.returned_at is None:
        raise ValueError('Cannot add fines to an open checkout.')
    created = 0
    for line in fine_lines:
        if line.amount < 0 or line.quantity < 1:
            continue
        DeviceFine.objects.create(
            checkout=checkout,
            fine_type_id=line.fine_type_id,
            description=line.description[:200],
            amount=line.amount,
            quantity=line.quantity,
            is_late_fee=line.is_late_fee,
            notes=line.notes or '',
            assessed_by=actor,
        )
        created += 1
    return created


@transaction.atomic
def set_fine_status(*, fine: DeviceFine, actor, new_status: str) -> None:
    fine.status = new_status
    fine.save(update_fields=['status'])
