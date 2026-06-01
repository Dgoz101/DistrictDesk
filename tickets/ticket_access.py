"""Ticket visibility helpers (submitter or administrator)."""


def user_can_access_ticket(user, ticket) -> bool:
    if not user.is_authenticated:
        return False
    if getattr(user, 'is_administrator', False):
        return True
    return ticket.submitter_id == user.id
