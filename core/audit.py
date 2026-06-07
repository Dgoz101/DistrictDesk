"""Append-only administrator audit logging."""
from __future__ import annotations

from .models import AdminAuditEntry


def _display_user(user) -> str:
    if user is None:
        return '—'
    return user.email or user.username


def log_field_changes(
    actor,
    *,
    action: str,
    entity_type: str,
    object_label: str,
    changes: dict[str, tuple[str, str]],
    object_id: int | None = None,
    ticket=None,
) -> int:
    """
    Write one audit row per changed field. Returns number of rows created.
    Skips fields where old_value == new_value.
    """
    if not changes or actor is None:
        return 0
    rows = []
    for field_name, (old_value, new_value) in changes.items():
        old_s = '' if old_value is None else str(old_value)
        new_s = '' if new_value is None else str(new_value)
        if old_s == new_s:
            continue
        rows.append(
            AdminAuditEntry(
                action=action,
                entity_type=entity_type,
                object_id=object_id,
                object_label=object_label[:255],
                field_name=field_name,
                old_value=old_s,
                new_value=new_s,
                actor=actor,
                ticket=ticket,
            )
        )
    if rows:
        AdminAuditEntry.objects.bulk_create(rows)
    return len(rows)


def log_create(
    actor,
    *,
    entity_type: str,
    instance,
    fields: dict[str, str],
    ticket=None,
) -> None:
    """Log entity creation with initial field values."""
    label = str(instance)
    changes = {k: ('', v) for k, v in fields.items()}
    log_field_changes(
        actor,
        action=AdminAuditEntry.Action.CREATE,
        entity_type=entity_type,
        object_label=label,
        changes=changes,
        object_id=instance.pk,
        ticket=ticket,
    )


def log_delete(
    actor,
    *,
    entity_type: str,
    object_label: str,
    object_id: int | None = None,
    ticket=None,
) -> None:
    AdminAuditEntry.objects.create(
        action=AdminAuditEntry.Action.DELETE,
        entity_type=entity_type,
        object_id=object_id,
        object_label=object_label[:255],
        field_name='',
        old_value=object_label[:255],
        new_value='',
        actor=actor,
        ticket=ticket,
    )


def _client_ip(request) -> str:
    if request is None:
        return ''
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or ''


def log_auth_login(*, user, request, success: bool, identifier: str = '') -> None:
    """
    Record sign-in success or failure. Failures have no actor (unknown user).
    `identifier` is the submitted email/username on failure.
    """
    if success and user is not None:
        label = _display_user(user)
        object_id = user.pk
        actor = user
        outcome = 'success'
    else:
        label = (identifier or 'unknown').strip()[:255]
        object_id = None
        actor = None
        outcome = 'failure'

    ip = _client_ip(request)
    detail = outcome
    if ip:
        detail = f'{outcome} ({ip})'

    AdminAuditEntry.objects.create(
        action=AdminAuditEntry.Action.LOGIN,
        entity_type=AdminAuditEntry.EntityType.AUTH,
        object_id=object_id,
        object_label=label,
        field_name='outcome',
        old_value='',
        new_value=detail,
        actor=actor,
    )


def log_auth_logout(*, user, request) -> None:
    if user is None:
        return
    ip = _client_ip(request)
    detail = 'logout'
    if ip:
        detail = f'logout ({ip})'
    AdminAuditEntry.objects.create(
        action=AdminAuditEntry.Action.LOGOUT,
        entity_type=AdminAuditEntry.EntityType.AUTH,
        object_id=user.pk,
        object_label=_display_user(user),
        field_name='outcome',
        old_value='',
        new_value=detail,
        actor=user,
    )


def log_user_admin_update(actor, user, *, old_role_name: str, new_role_name: str, old_active: bool, new_active: bool) -> None:
    label = _display_user(user)
    changes = {}
    if old_role_name != new_role_name:
        changes['role'] = (old_role_name or '—', new_role_name or '—')
    if old_active != new_active:
        changes['is_active'] = ('Yes' if old_active else 'No', 'Yes' if new_active else 'No')
    log_field_changes(
        actor,
        action=AdminAuditEntry.Action.UPDATE,
        entity_type=AdminAuditEntry.EntityType.USER,
        object_label=label,
        changes=changes,
        object_id=user.pk,
    )


def log_ticket_lookup_change(actor, instance, *, entity_type: str, old_fields: dict, new_fields: dict) -> None:
    changes = {}
    for key in new_fields:
        old_v = old_fields.get(key, '')
        new_v = new_fields.get(key, '')
        if str(old_v) != str(new_v):
            changes[key] = (str(old_v), str(new_v))
    if not changes:
        return
    log_field_changes(
        actor,
        action=AdminAuditEntry.Action.UPDATE,
        entity_type=entity_type,
        object_label=str(instance),
        changes=changes,
        object_id=instance.pk,
    )


def log_ticket_field_changes(
    actor,
    ticket,
    *,
    category_change=None,
    priority_change=None,
    due_change=None,
) -> None:
    """category_change / priority_change / due_change: optional (old, new) tuples."""
    changes = {}
    if category_change:
        changes['category'] = category_change
    if priority_change:
        changes['priority'] = priority_change
    if due_change:
        changes['due date'] = due_change
    if not changes:
        return
    log_field_changes(
        actor,
        action=AdminAuditEntry.Action.UPDATE,
        entity_type=AdminAuditEntry.EntityType.TICKET,
        object_label=f'#{ticket.pk} {ticket.title}'[:255],
        changes=changes,
        object_id=ticket.pk,
        ticket=ticket,
    )


def build_ticket_activity_timeline(ticket):
    """
    Merge status history, assignments, and ticket-scoped audit rows for the detail page.
    Returns list of dicts sorted by time ascending.
    """
    events = []

    for row in ticket.status_history.select_related('changed_by').all():
        if row.old_status:
            summary = f'Status: {row.old_status} → {row.new_status}'
        else:
            summary = f'Status: {row.new_status}'
        events.append({
            'at': row.changed_at,
            'kind': 'status',
            'summary': summary,
            'actor': row.changed_by,
        })

    for assignment in ticket.assignments.select_related('assigned_to', 'assigned_by').order_by('assigned_at'):
        assignee = _display_user(assignment.assigned_to)
        suffix = ' (current)' if assignment.is_current else ''
        events.append({
            'at': assignment.assigned_at,
            'kind': 'assignment',
            'summary': f'Assigned to {assignee}{suffix}',
            'actor': assignment.assigned_by,
        })

    for entry in ticket.audit_entries.select_related('actor').all():
        if entry.field_name:
            label = entry.field_name.replace('_', ' ').title()
            summary = f'{label}: {entry.old_value} → {entry.new_value}'
        else:
            summary = f'{entry.get_action_display()} {entry.object_label}'
        events.append({
            'at': entry.created_at,
            'kind': 'audit',
            'summary': summary,
            'actor': entry.actor,
        })

    events.sort(key=lambda e: e['at'])
    return events
