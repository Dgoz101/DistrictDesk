"""Create, list, and remove undirected ticket relations."""
from __future__ import annotations

from django.db.models import Q

from .models import Ticket, TicketRelation


def normalize_ticket_pair(ticket_a: Ticket, ticket_b: Ticket) -> tuple[Ticket, Ticket]:
    if ticket_a.pk == ticket_b.pk:
        raise ValueError('A ticket cannot be related to itself.')
    if ticket_a.pk < ticket_b.pk:
        return ticket_a, ticket_b
    return ticket_b, ticket_a


def link_tickets(
    ticket: Ticket,
    other: Ticket,
    *,
    relation_type: str,
    created_by,
    note: str = '',
) -> TicketRelation:
    low, high = normalize_ticket_pair(ticket, other)
    existing = TicketRelation.objects.filter(ticket_low=low, ticket_high=high).first()
    if existing:
        existing.relation_type = relation_type
        existing.note = (note or '').strip()
        existing.save(update_fields=['relation_type', 'note'])
        return existing
    return TicketRelation.objects.create(
        ticket_low=low,
        ticket_high=high,
        relation_type=relation_type,
        note=(note or '').strip(),
        created_by=created_by,
    )


def relations_for_ticket(ticket: Ticket):
    return (
        TicketRelation.objects.filter(Q(ticket_low=ticket) | Q(ticket_high=ticket))
        .select_related('ticket_low', 'ticket_high', 'created_by')
        .order_by('-created_at')
    )


def related_ticket_rows(ticket: Ticket) -> list[dict]:
    """Rows for the detail page: other ticket, type, note, relation pk."""
    rows = []
    for rel in relations_for_ticket(ticket):
        other = rel.other_ticket(ticket)
        rows.append({
            'relation': rel,
            'other': other,
            'relation_type': rel.relation_type,
            'relation_type_label': rel.get_relation_type_display(),
            'note': rel.note,
        })
    return rows
