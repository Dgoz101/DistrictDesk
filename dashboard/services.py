"""
Read-only aggregations for the administrator dashboard (FR-31–FR-35).
"""
from datetime import timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.db.models.functions import TruncDate
from django.utils import timezone

from devices.models import Device
from tickets.models import Ticket


def _duration_to_hours(td):
    if td is None:
        return None
    return round(td.total_seconds() / 3600.0, 2)


def get_dashboard_data():
    """
    Build summary numbers and chart-friendly structures for the dashboard template and API.
    """
    today = timezone.localdate()
    trend_start_date = today - timedelta(days=13)

    total_tickets = Ticket.objects.count()
    open_statuses = (
        Ticket.Status.OPEN,
        Ticket.Status.ASSIGNED,
        Ticket.Status.IN_PROGRESS,
    )
    open_tickets = Ticket.objects.filter(status__in=open_statuses).count()

    status_rows = (
        Ticket.objects.values('status')
        .annotate(count=Count('id'))
        .order_by('status')
    )
    status_labels = [r['status'] for r in status_rows]
    status_counts = [r['count'] for r in status_rows]

    category_rows = (
        Ticket.objects.values('category__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    category_labels = [r['category__name'] or '—' for r in category_rows]
    category_counts = [r['count'] for r in category_rows]

    # Last 14 calendar days of ticket volume (trend)
    day_counts = {}
    for row in (
        Ticket.objects.filter(created_at__date__gte=trend_start_date)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
    ):
        d = row['day']
        if d is not None:
            day_counts[d] = row['count']

    trend_labels = []
    trend_counts = []
    for i in range(14):
        d = trend_start_date + timedelta(days=i)
        trend_labels.append(d.isoformat())
        trend_counts.append(day_counts.get(d, 0))

    resolved = Ticket.objects.filter(closed_at__isnull=False)
    avg_delta = resolved.annotate(
        dur=ExpressionWrapper(F('closed_at') - F('created_at'), output_field=DurationField())
    ).aggregate(avg=Avg('dur'))['avg']
    avg_resolution_hours = _duration_to_hours(avg_delta)

    total_devices = Device.objects.count()

    dtype_rows = (
        Device.objects.values('device_type__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    dtype_labels = [r['device_type__name'] or '—' for r in dtype_rows]
    dtype_counts = [r['count'] for r in dtype_rows]

    dstatus_rows = (
        Device.objects.values('status__name')
        .annotate(count=Count('id'))
        .order_by('status__name')
    )
    dstatus_labels = [r['status__name'] or '—' for r in dstatus_rows]
    dstatus_counts = [r['count'] for r in dstatus_rows]

    return {
        'summary': {
            'total_tickets': total_tickets,
            'open_tickets': open_tickets,
            'total_devices': total_devices,
            'avg_resolution_hours': avg_resolution_hours,
        },
        'chart_data': {
            'tickets_by_status': {'labels': status_labels, 'counts': status_counts},
            'tickets_by_category': {'labels': category_labels, 'counts': category_counts},
            'tickets_trend': {'labels': trend_labels, 'counts': trend_counts},
            'devices_by_type': {'labels': dtype_labels, 'counts': dtype_counts},
            'devices_by_status': {'labels': dstatus_labels, 'counts': dstatus_counts},
        },
        'generated_at': timezone.now(),
    }
