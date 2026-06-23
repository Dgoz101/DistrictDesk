"""CSV export for tickets (admin; respects list filters)."""
from __future__ import annotations

from typing import Iterable

from django.utils import timezone

from .models import Ticket
from .sla_service import ticket_is_overdue

EXPORT_FIELDNAMES = [
    'id',
    'title',
    'description',
    'status',
    'category',
    'priority',
    'submitter',
    'assigned_to',
    'device_asset_tag',
    'location',
    'contact_info',
    'created_at',
    'updated_at',
    'closed_at',
    'due_at',
    'overdue',
]


def _format_dt(value) -> str:
    if not value:
        return ''
    if timezone.is_naive(value):
        value = timezone.make_aware(value)
    return timezone.localtime(value).strftime('%Y-%m-%d %H:%M')


def _user_label(user) -> str:
    if user is None:
        return ''
    return user.email or user.username or ''


def ticket_to_row(ticket: Ticket) -> dict[str, str]:
    assigned = []
    for assignment in ticket.assignments.all():
        if assignment.is_current:
            assigned.append(_user_label(assignment.assigned_to))
    return {
        'id': str(ticket.pk),
        'title': ticket.title,
        'description': ticket.description,
        'status': ticket.status,
        'category': ticket.category.name if ticket.category_id else '',
        'priority': ticket.priority.name if ticket.priority_id else '',
        'submitter': _user_label(ticket.submitter),
        'assigned_to': ', '.join(assigned),
        'device_asset_tag': ticket.device.asset_tag if ticket.device_id else '',
        'location': ticket.location.name if ticket.location_id else '',
        'contact_info': ticket.contact_info or '',
        'created_at': _format_dt(ticket.created_at),
        'updated_at': _format_dt(ticket.updated_at),
        'closed_at': _format_dt(ticket.closed_at),
        'due_at': _format_dt(ticket.due_at),
        'overdue': 'yes' if ticket_is_overdue(ticket) else 'no',
    }


def iter_export_rows(tickets: Iterable[Ticket]):
    for ticket in tickets:
        yield ticket_to_row(ticket)
