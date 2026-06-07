from datetime import timedelta

from django.db import migrations, models
from django.utils import timezone


DEFAULT_PRIORITY_DUE_DAYS = {
    'Low': 14,
    'Medium': 7,
    'High': 3,
    'Critical': 1,
}


def seed_priority_due_days(apps, schema_editor):
    PriorityLevel = apps.get_model('tickets', 'PriorityLevel')
    Ticket = apps.get_model('tickets', 'Ticket')
    for name, days in DEFAULT_PRIORITY_DUE_DAYS.items():
        PriorityLevel.objects.filter(name=name, due_days__isnull=True).update(due_days=days)

    for ticket in Ticket.objects.filter(due_at__isnull=True).select_related('priority'):
        days = getattr(ticket.priority, 'due_days', None)
        if days:
            created = ticket.created_at
            if timezone.is_naive(created):
                created = timezone.make_aware(created)
            ticket.due_at = created + timedelta(days=days)
            ticket.due_at_is_manual = False
            ticket.save(update_fields=['due_at', 'due_at_is_manual'])


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0002_ticket_attachments'),
    ]

    operations = [
        migrations.AddField(
            model_name='prioritylevel',
            name='due_days',
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text='SLA target: days from ticket creation until due (blank = no auto due date).',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='ticket',
            name='due_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Target resolution date (from priority SLA or set manually).',
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='ticket',
            name='due_at_is_manual',
            field=models.BooleanField(
                default=False,
                help_text='When set, priority changes do not recalculate due_at.',
            ),
        ),
        migrations.AddIndex(
            model_name='ticket',
            index=models.Index(fields=['due_at'], name='tickets_tic_due_at_idx'),
        ),
        migrations.RunPython(seed_priority_due_days, migrations.RunPython.noop),
    ]
