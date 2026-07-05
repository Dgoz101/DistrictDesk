"""Shared queryset builder for ticket list and admin CSV export."""
from django.db.models import Prefetch, Q
from django.utils import timezone

from .models import Ticket, TicketAssignment
from .aging import apply_aging_list_filters
from .sla_service import OPEN_STATUSES


def _base_ticket_queryset():
    return Ticket.objects.select_related(
        'category', 'priority', 'submitter', 'device', 'location'
    ).prefetch_related(
        Prefetch(
            'assignments',
            queryset=TicketAssignment.objects.filter(is_current=True).select_related(
                'assigned_to'
            ),
        )
    )


def _apply_admin_list_filters(qs, params):
    q = (params.get('q') or '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    status = params.get('status')
    if status:
        qs = qs.filter(status=status)

    category = params.get('category')
    if category:
        qs = qs.filter(category_id=category)

    priority = params.get('priority')
    if priority:
        qs = qs.filter(priority_id=priority)

    assigned = params.get('assigned')
    if assigned:
        qs = qs.filter(
            assignments__assigned_to_id=assigned,
            assignments__is_current=True,
        ).distinct()

    if params.get('overdue') == '1':
        now = timezone.now()
        qs = qs.filter(due_at__lt=now, status__in=OPEN_STATUSES)

    qs = apply_aging_list_filters(qs, params)

    sort = params.get('sort', '-created_at')
    if sort == 'priority':
        qs = qs.order_by('priority__sort_order', '-created_at')
    elif sort == '-priority':
        qs = qs.order_by('-priority__sort_order', '-created_at')
    elif sort == 'status':
        qs = qs.order_by('status', '-created_at')
    elif sort == '-status':
        qs = qs.order_by('-status', '-created_at')
    elif sort == 'created_at':
        qs = qs.order_by('created_at')
    elif sort == 'due_at':
        qs = qs.order_by('due_at', '-created_at')
    elif sort == '-due_at':
        qs = qs.order_by('-due_at', '-created_at')
    else:
        qs = qs.order_by('-created_at')
    return qs


def build_ticket_list_queryset(request):
    """Tickets for list view or export: own tickets for standard users; filtered all for admins."""
    qs = _base_ticket_queryset()
    if not request.user.is_administrator:
        return qs.filter(submitter=request.user).order_by('-created_at')
    return _apply_admin_list_filters(qs, request.GET)
