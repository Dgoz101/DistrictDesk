"""Open-ticket age buckets and list filters for dashboard aging KPI/chart."""
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .sla_service import OPEN_STATUSES

# (bucket id, chart label, min_days inclusive, max_days exclusive for upper bound)
TICKET_AGING_BUCKETS = (
    ('0-6', 'Under 7 days', 0, 7),
    ('7-13', '7–13 days', 7, 14),
    ('14-29', '14–29 days', 14, 30),
    ('30plus', '30+ days', 30, None),
)


def aging_threshold_days() -> int:
    return int(getattr(settings, 'DASHBOARD_TICKET_AGING_DAYS', 7))


def _open_tickets_qs():
    from .models import Ticket

    return Ticket.objects.filter(status__in=OPEN_STATUSES)


def filter_open_tickets_by_age(qs, *, min_days: int = 0, max_days: int | None = None, now=None):
    """Restrict queryset to open tickets in an age range (days since created)."""
    now = now or timezone.now()
    qs = qs.filter(status__in=OPEN_STATUSES)
    if max_days is not None:
        qs = qs.filter(created_at__gt=now - timedelta(days=max_days))
    if min_days > 0:
        qs = qs.filter(created_at__lte=now - timedelta(days=min_days))
    return qs


def apply_aging_list_filters(qs, params, *, now=None):
    """Apply aging_days (N+ days open) or aging_bucket from GET params."""
    now = now or timezone.now()
    bucket = (params.get('aging_bucket') or '').strip()
    for bucket_id, _label, min_days, max_days in TICKET_AGING_BUCKETS:
        if bucket == bucket_id:
            return filter_open_tickets_by_age(qs, min_days=min_days, max_days=max_days, now=now)

    raw = (params.get('aging_days') or '').strip()
    if raw.isdigit():
        days = int(raw)
        if days > 0:
            return qs.filter(
                status__in=OPEN_STATUSES,
                created_at__lte=now - timedelta(days=days),
            )
    return qs


def aging_bucket_counts(*, now=None) -> list[dict]:
    """Counts per age bucket for open tickets."""
    now = now or timezone.now()
    base = _open_tickets_qs()
    rows = []
    for bucket_id, label, min_days, max_days in TICKET_AGING_BUCKETS:
        count = filter_open_tickets_by_age(base, min_days=min_days, max_days=max_days, now=now).count()
        rows.append({'id': bucket_id, 'label': label, 'count': count})
    return rows


def aging_open_count(*, threshold_days: int | None = None, now=None) -> int:
    """Open tickets at least threshold_days old."""
    threshold_days = aging_threshold_days() if threshold_days is None else threshold_days
    now = now or timezone.now()
    if threshold_days <= 0:
        return _open_tickets_qs().count()
    return _open_tickets_qs().filter(
        created_at__lte=now - timedelta(days=threshold_days),
    ).count()


def aging_open_preview(*, limit: int = 10, threshold_days: int | None = None, now=None) -> list[dict]:
    """Oldest open tickets at or past the aging threshold."""
    threshold_days = aging_threshold_days() if threshold_days is None else threshold_days
    now = now or timezone.now()
    qs = _open_tickets_qs().order_by('created_at')
    if threshold_days > 0:
        qs = qs.filter(created_at__lte=now - timedelta(days=threshold_days))
    return [
        {
            'id': t.pk,
            'title': t.title,
            'status': t.status,
            'created_at': timezone.localtime(t.created_at).strftime('%Y-%m-%d %H:%M'),
        }
        for t in qs[:limit]
    ]
