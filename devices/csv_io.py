"""CSV import/export for device inventory (admin). Upsert key: asset_tag."""
from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime
from typing import BinaryIO, Iterable

from django.contrib.auth import get_user_model
from django.db import transaction

from core.models import Location

from .models import Device, DeviceStatus, DeviceType

User = get_user_model()


def _normalize_row_keys(row: dict[str, str]) -> dict[str, str]:
    return {(k or '').strip().lower(): (v if v is not None else '') for k, v in row.items()}

EXPORT_FIELDNAMES = [
    'asset_tag',
    'device_type',
    'status',
    'model',
    'serial_number',
    'location',
    'assigned_user',
    'purchase_date',
    'warranty_end_date',
    'purchase_vendor',
    'purchase_order',
    'public_report_uuid',
]


def _parse_date(s: str | None) -> date | None:
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_uuid(s: str | None):
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    try:
        return uuid.UUID(s)
    except ValueError:
        return None


def _lookup_ci(qs, name: str):
    if not name or not str(name).strip():
        return None
    return qs.filter(name__iexact=str(name).strip()).first()


def _resolve_user(raw: str | None):
    if raw is None:
        return None
    v = str(raw).strip()
    if not v:
        return None
    u = User.objects.filter(email__iexact=v).first()
    if u:
        return u
    return User.objects.filter(username__iexact=v).first()


def device_to_row(device: Device) -> dict[str, str]:
    loc = device.location.name if device.location_id else ''
    au = ''
    if device.assigned_user_id:
        u = device.assigned_user
        au = u.email or u.username
    return {
        'asset_tag': device.asset_tag,
        'device_type': device.device_type.name,
        'status': device.status.name,
        'model': device.model or '',
        'serial_number': device.serial_number or '',
        'location': loc,
        'assigned_user': au,
        'purchase_date': device.purchase_date.isoformat() if device.purchase_date else '',
        'warranty_end_date': device.warranty_end_date.isoformat() if device.warranty_end_date else '',
        'purchase_vendor': device.purchase_vendor or '',
        'purchase_order': device.purchase_order or '',
        'public_report_uuid': str(device.public_report_uuid),
    }


def iter_export_rows(devices: Iterable[Device]):
    for d in devices:
        yield device_to_row(d)


def parse_upload(file: BinaryIO) -> tuple[list[str], list[dict[str, str]]]:
    raw = file.read()
    if isinstance(raw, str):
        text = raw
    else:
        text = raw.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return [], []
    fnames = [f.strip() for f in reader.fieldnames if f]
    rows = []
    for row in reader:
        rows.append({(k or '').strip(): (v if v is not None else '') for k, v in row.items()})
    return fnames, rows


def _prepare_row(row: dict[str, str]) -> tuple[str | None, dict | None]:
    """
    Validate and build kwargs for create/update. Returns (error, prepared) where prepared has keys:
    asset_tag, device_type, status, model, serial_number, location, assigned_user,
    purchase_date, warranty_end_date, purchase_vendor, purchase_order, public_report_uuid (optional)
    """
    asset_tag = (row.get('asset_tag') or '').strip()
    if not asset_tag:
        return 'asset_tag is required', None

    dtype = _lookup_ci(DeviceType.objects.all(), row.get('device_type') or '')
    if not dtype:
        return f'unknown device_type: {row.get("device_type")!r}', None

    dst = _lookup_ci(DeviceStatus.objects.all(), row.get('status') or '')
    if not dst:
        return f'unknown status: {row.get("status")!r}', None

    loc_name = (row.get('location') or '').strip()
    loc = None
    if loc_name:
        loc = _lookup_ci(Location.objects.all(), loc_name)
        if not loc:
            return f'unknown location: {loc_name!r}', None

    au_raw = row.get('assigned_user')
    user = _resolve_user(au_raw)
    if (au_raw or '').strip() and user is None:
        return f'unknown assigned_user: {au_raw!r}', None

    pd = _parse_date(row.get('purchase_date'))
    if (row.get('purchase_date') or '').strip() and pd is None:
        return f'invalid purchase_date: {row.get("purchase_date")!r}', None

    wd = _parse_date(row.get('warranty_end_date'))
    if (row.get('warranty_end_date') or '').strip() and wd is None:
        return f'invalid warranty_end_date: {row.get("warranty_end_date")!r}', None

    pub = _parse_uuid(row.get('public_report_uuid'))
    if (row.get('public_report_uuid') or '').strip() and pub is None:
        return f'invalid public_report_uuid: {row.get("public_report_uuid")!r}', None

    prepared = {
        'asset_tag': asset_tag,
        'device_type': dtype,
        'status': dst,
        'model': (row.get('model') or '').strip(),
        'serial_number': (row.get('serial_number') or '').strip(),
        'location': loc,
        'assigned_user': user,
        'purchase_date': pd,
        'warranty_end_date': wd,
        'purchase_vendor': (row.get('purchase_vendor') or '').strip(),
        'purchase_order': (row.get('purchase_order') or '').strip(),
        'public_report_uuid': pub,
    }
    return None, prepared


def _apply_prepared(prepared: dict) -> str:
    """Persist prepared row. Returns 'created' or 'updated'."""
    asset_tag = prepared['asset_tag']
    pub = prepared.pop('public_report_uuid', None)
    existing = Device.objects.filter(asset_tag=asset_tag).first()
    if existing:
        for k, v in prepared.items():
            setattr(existing, k, v)
        if pub is not None:
            if Device.objects.filter(public_report_uuid=pub).exclude(pk=existing.pk).exists():
                raise ValueError('public_report_uuid already used by another device')
            existing.public_report_uuid = pub
        existing.save()
        return 'updated'

    kwargs = {**prepared}
    if pub is not None:
        if Device.objects.filter(public_report_uuid=pub).exists():
            raise ValueError('public_report_uuid already used by another device')
        kwargs['public_report_uuid'] = pub
    Device.objects.create(**kwargs)
    return 'created'


def run_import(rows: list[dict[str, str]], *, dry_run: bool) -> dict:
    rows = [_normalize_row_keys(r) for r in rows]
    errors: list[dict] = []
    created = 0
    updated = 0
    line_base = 2

    prepared_rows: list[tuple[int, dict]] = []
    for i, row in enumerate(rows):
        line_no = line_base + i
        err, prep = _prepare_row(row)
        if err:
            errors.append({'line': line_no, 'message': err, 'asset_tag': (row.get('asset_tag') or '').strip()})
            continue
        assert prep is not None
        exists = Device.objects.filter(asset_tag=prep['asset_tag']).exists()
        action = 'updated' if exists else 'created'
        if dry_run:
            if action == 'created':
                created += 1
            else:
                updated += 1
            continue
        prepared_rows.append((line_no, prep))

    if dry_run:
        return {'errors': errors, 'created': created, 'updated': updated, 'dry_run': True}

    for line_no, prep in prepared_rows:
        try:
            with transaction.atomic():
                action = _apply_prepared(dict(prep))
                if action == 'created':
                    created += 1
                else:
                    updated += 1
        except ValueError as e:
            errors.append({'line': line_no, 'message': str(e), 'asset_tag': prep.get('asset_tag', '')})

    return {'errors': errors, 'created': created, 'updated': updated, 'dry_run': False}
