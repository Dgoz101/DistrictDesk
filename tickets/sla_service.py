"""Ticket SLA: due dates from priority or manual override."""
from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

from .models import Ticket

OPEN_STATUSES = frozenset({
    Ticket.Status.OPEN,
    Ticket.Status.ASSIGNED,
    Ticket.Status.IN_PROGRESS,
})


def due_at_from_priority(created_at: datetime, priority) -> datetime | None:
    """Target due datetime from priority SLA days, or None if not configured."""
    days = getattr(priority, 'due_days', None)
    if not days:
        return None
    base = created_at or timezone.now()
    if timezone.is_naive(base):
        base = timezone.make_aware(base)
    return base + timedelta(days=days)


def ticket_is_overdue(ticket: Ticket, *, at: datetime | None = None) -> bool:
    """True when past due and still in an open workflow status."""
    if not ticket.due_at or ticket.status not in OPEN_STATUSES:
        return False
    at = at or timezone.now()
    due = ticket.due_at
    if timezone.is_naive(due):
        due = timezone.make_aware(due)
    if timezone.is_naive(at):
        at = timezone.make_aware(at)
    return at > due


def apply_ticket_due_on_create(ticket: Ticket) -> None:
    """Set due_at from priority SLA after the ticket row exists."""
    ticket.due_at = due_at_from_priority(ticket.created_at, ticket.priority)
    ticket.due_at_is_manual = False
    ticket.save(update_fields=['due_at', 'due_at_is_manual', 'updated_at'])


def resolve_due_at_on_admin_update(
    ticket: Ticket,
    *,
    priority,
    form_due_at,
    due_at_changed: bool,
    priority_changed: bool,
) -> tuple[datetime | None, bool]:
    """
    Decide due_at and due_at_is_manual after an admin update.
    Returns (due_at, due_at_is_manual).
    """
    if due_at_changed:
        return form_due_at, True
    if priority_changed and not ticket.due_at_is_manual:
        return due_at_from_priority(ticket.created_at, priority), False
    return ticket.due_at, ticket.due_at_is_manual
