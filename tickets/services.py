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


def apply_admin_ticket_update(ticket, user, *, category, priority, new_status, old_status):
    """
    Update category, priority, and status from admin form.
    Records status history only when status changes; sets closed_at for Resolved/Closed (FR-22).
    `old_status` must be captured before binding the POST form to the instance.
    """
    ticket.category = category
    ticket.priority = priority
    if new_status != old_status:
        ticket.status = new_status
        if new_status in (Ticket.Status.RESOLVED, Ticket.Status.CLOSED):
            ticket.closed_at = timezone.now()
        else:
            ticket.closed_at = None
        ticket.save()
        record_status_change(ticket, old_status, new_status, user)
    else:
        ticket.save(update_fields=['category', 'priority', 'updated_at'])


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
