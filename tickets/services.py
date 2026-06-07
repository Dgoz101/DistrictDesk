"""Ticket workflow: status history, assignment (FR-18, FR-36–FR-37)."""
from django.db import transaction
from django.utils import timezone

from .models import Ticket, TicketAssignment, TicketStatusHistory


def record_ticket_created(ticket, user):
    """First status row when a ticket is submitted (FR-17, FR-36)."""
    TicketStatusHistory.objects.create(
        ticket=ticket,
        old_status='',
        new_status=ticket.status,
        changed_by=user,
    )


def record_status_change(ticket, old_status, new_status, user):
    """Append a status change to history."""
    TicketStatusHistory.objects.create(
        ticket=ticket,
        old_status=old_status or '',
        new_status=new_status,
        changed_by=user,
    )


def _format_due_at(value):
    if value is None:
        return '—'
    return timezone.localtime(value).strftime('%Y-%m-%d %H:%M')


def apply_admin_ticket_update(
    ticket,
    user,
    *,
    category,
    priority,
    new_status,
    old_status,
    old_category=None,
    old_priority=None,
    due_at=None,
    old_due_at=None,
    due_at_changed: bool = False,
):
    """
    Update category, priority, status, and due date from admin form.
    Records status history only when status changes; sets closed_at for Resolved/Closed (FR-22).
    `old_status` must be captured before binding the POST form to the instance.
    """
    from core.audit import log_ticket_field_changes
    from .sla_service import resolve_due_at_on_admin_update

    ticket.category = category
    ticket.priority = priority
    cat_change = None
    pri_change = None
    due_change = None
    if old_category is not None and old_category.pk != category.pk:
        cat_change = (old_category.name, category.name)
    priority_changed = old_priority is not None and old_priority.pk != priority.pk
    if priority_changed:
        pri_change = (old_priority.name, priority.name)

    old_manual = ticket.due_at_is_manual
    new_due_at, new_manual = resolve_due_at_on_admin_update(
        ticket,
        priority=priority,
        form_due_at=due_at,
        due_at_changed=due_at_changed,
        priority_changed=priority_changed,
    )
    if old_due_at != new_due_at or old_manual != new_manual:
        due_change = (_format_due_at(old_due_at), _format_due_at(new_due_at))
    ticket.due_at = new_due_at
    ticket.due_at_is_manual = new_manual

    update_fields = ['category', 'priority', 'due_at', 'due_at_is_manual', 'updated_at']

    if new_status != old_status:
        ticket.status = new_status
        if new_status in (Ticket.Status.RESOLVED, Ticket.Status.CLOSED):
            ticket.closed_at = timezone.now()
        else:
            ticket.closed_at = None
        update_fields.extend(['status', 'closed_at'])
        ticket.save(update_fields=update_fields)
        record_status_change(ticket, old_status, new_status, user)
    else:
        ticket.save(update_fields=update_fields)

    log_ticket_field_changes(
        user,
        ticket,
        category_change=cat_change,
        priority_change=pri_change,
        due_change=due_change,
    )


def assign_ticket(ticket, assignee, assigned_by):
    """
    Create a new current assignment; clear previous current (FR-18, FR-37).
    If ticket was Open, move to Assigned and record status history.
    """
    with transaction.atomic():
        TicketAssignment.objects.filter(ticket=ticket, is_current=True).update(is_current=False)
        TicketAssignment.objects.create(
            ticket=ticket,
            assigned_to=assignee,
            assigned_by=assigned_by,
            is_current=True,
        )
        if ticket.status == Ticket.Status.OPEN:
            old = ticket.status
            ticket.status = Ticket.Status.ASSIGNED
            ticket.save(update_fields=['status', 'updated_at'])
            record_status_change(ticket, old, ticket.status, assigned_by)
