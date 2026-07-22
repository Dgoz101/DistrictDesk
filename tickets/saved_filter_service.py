"""Saved ticket list filters for administrators/techs."""
from __future__ import annotations

from urllib.parse import urlencode

from django.db import transaction
from django.urls import reverse

from .models import SavedTicketFilter

# Query keys that can be stored on a saved filter (excludes page, skip_default).
FILTER_PARAM_KEYS = (
    'q',
    'status',
    'category',
    'priority',
    'location',
    'assigned',
    'overdue',
    'aging_days',
    'aging_bucket',
    'sort',
)


def extract_filter_params(querydict) -> dict[str, str]:
    """Normalize request GET/POST into a compact params dict."""
    params: dict[str, str] = {}
    for key in FILTER_PARAM_KEYS:
        raw = querydict.get(key)
        if raw is None:
            continue
        value = str(raw).strip()
        if not value:
            continue
        if key == 'sort' and value == '-created_at':
            continue
        params[key] = value
    return params


def has_active_filters(querydict) -> bool:
    return bool(extract_filter_params(querydict))


def params_to_querystring(params: dict) -> str:
    clean = {k: str(v) for k, v in (params or {}).items() if v not in (None, '')}
    return urlencode(clean)


def saved_filter_list_url(saved: SavedTicketFilter) -> str:
    qs = params_to_querystring(saved.params or {})
    base = reverse('tickets:list')
    return f'{base}?{qs}' if qs else base


def default_saved_filter(user) -> SavedTicketFilter | None:
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    return (
        SavedTicketFilter.objects.filter(user=user, is_default=True)
        .order_by('name')
        .first()
    )


def default_ticket_list_url(user) -> str | None:
    saved = default_saved_filter(user)
    if not saved:
        return None
    return saved_filter_list_url(saved)


@transaction.atomic
def save_ticket_filter(*, user, name: str, params: dict, is_default: bool) -> SavedTicketFilter:
    name = (name or '').strip()
    if not name:
        raise ValueError('Name is required.')
    params = extract_filter_params(params) if not isinstance(params, dict) else {
        k: str(v).strip()
        for k, v in params.items()
        if k in FILTER_PARAM_KEYS and str(v).strip()
    }
    if is_default:
        SavedTicketFilter.objects.filter(user=user, is_default=True).update(is_default=False)
    obj, _created = SavedTicketFilter.objects.update_or_create(
        user=user,
        name=name,
        defaults={'params': params, 'is_default': is_default},
    )
    return obj


@transaction.atomic
def set_default_saved_filter(*, user, saved: SavedTicketFilter) -> None:
    SavedTicketFilter.objects.filter(user=user, is_default=True).update(is_default=False)
    saved.is_default = True
    saved.save(update_fields=['is_default', 'updated_at'])
