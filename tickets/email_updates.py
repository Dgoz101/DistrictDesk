"""
Email notifications for ticket lifecycle (optional per user via User.email_ticket_updates).
Uses Django's email framework (console backend in development, SMTP in production).
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

logger = logging.getLogger(__name__)


def _recipient_address(user):
    return (user.email or user.username or '').strip()


def _wants_ticket_mail(user):
    return bool(getattr(user, 'email_ticket_updates', True))


def _append_ticket_link(request, ticket, lines):
    if request is None or ticket is None:
        return
    url = request.build_absolute_uri(reverse('tickets:detail', kwargs={'pk': ticket.pk}))
    lines.append('')
    lines.append(f'View ticket: {url}')


def _send_plain(user, subject, body_lines, *, request=None, ticket=None):
    if not _wants_ticket_mail(user):
        return
    recipient = _recipient_address(user)
    if not recipient:
        return
    lines = list(body_lines)
    _append_ticket_link(request, ticket, lines)
    text = '\n'.join(lines)
    try:
        send_mail(
            subject,
            text,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
    except Exception:
        logger.exception('Ticket notification email failed (to=%s, subject=%s)', recipient, subject)


def notify_submitter_ticket_changes(ticket, request, summary_lines):
    """Submitter: status/category/priority changes from an administrator."""
    if not summary_lines:
        return
    submitter = ticket.submitter
    subject = f'[DistrictDesk] Ticket #{ticket.pk} updated: {ticket.title}'
    body = ['Your support ticket was updated.', ''] + summary_lines
    _send_plain(submitter, subject, body, request=request, ticket=ticket)


def notify_submitter_assigned(ticket, request, assignee):
    """Submitter: ticket was assigned to IT staff."""
    submitter = ticket.submitter
    who = assignee.email or assignee.username
    subject = f'[DistrictDesk] Ticket #{ticket.pk} assigned: {ticket.title}'
    body = [
        'Your support ticket has been assigned.',
        '',
        f'Assigned to: {who}',
    ]
    _send_plain(submitter, subject, body, request=request, ticket=ticket)


def notify_assignee_assigned(ticket, request, assignee):
    """Assignee: you were assigned this ticket (same opt-in flag)."""
    if assignee.pk == ticket.submitter_id:
        return
    who = ticket.submitter.email or ticket.submitter.username
    subject = f'[DistrictDesk] You were assigned ticket #{ticket.pk}'
    body = [
        f'You have been assigned ticket #{ticket.pk}.',
        '',
        f'Title: {ticket.title}',
        f'Submitted by: {who}',
    ]
    _send_plain(assignee, subject, body, request=request, ticket=ticket)


def notify_submitter_public_comment(ticket, request, author, comment_body):
    """Submitter: new non-internal comment (visible to them in the app)."""
    submitter = ticket.submitter
    author_label = author.email or author.username
    subject = f'[DistrictDesk] New reply on ticket #{ticket.pk}'
    body = [
        f'{author_label} added a comment to your ticket:',
        '',
        comment_body.strip(),
    ]
    _send_plain(submitter, subject, body, request=request, ticket=ticket)
