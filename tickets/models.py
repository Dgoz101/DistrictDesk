import uuid

from django.conf import settings
from django.db import models

from core.models import Location


def ticket_attachment_upload_to(instance, filename):
    """Store under UUID; original filename kept on the model."""
    ext = ''
    if instance.original_filename:
        from pathlib import PurePath

        ext = PurePath(instance.original_filename).suffix.lower()
    return f'tickets/attachments/{uuid.uuid4().hex}{ext}'


class TicketCategory(models.Model):
    """Configurable category (FR-39): Hardware, Software, Access, etc."""
    name = models.CharField(max_length=100)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'tickets_ticketcategory'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class PriorityLevel(models.Model):
    """Configurable priority (FR-39): Low, Medium, High, Critical."""
    name = models.CharField(max_length=50)
    sort_order = models.IntegerField(default=0)
    due_days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text='SLA target: days from ticket creation until due (blank = no auto due date).',
    )

    class Meta:
        db_table = 'tickets_prioritylevel'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Ticket(models.Model):
    """Support ticket (FR-10–FR-17, FR-30)."""
    class Status(models.TextChoices):
        OPEN = 'Open', 'Open'
        ASSIGNED = 'Assigned', 'Assigned'
        IN_PROGRESS = 'In Progress', 'In Progress'
        RESOLVED = 'Resolved', 'Resolved'
        CLOSED = 'Closed', 'Closed'

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(TicketCategory, on_delete=models.PROTECT, related_name='tickets')
    priority = models.ForeignKey(PriorityLevel, on_delete=models.PROTECT, related_name='tickets')
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.OPEN)
    submitter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='submitted_tickets',
    )
    device = models.ForeignKey(
        'devices.Device',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
    )
    contact_info = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Target resolution date (from priority SLA or set manually).',
    )
    due_at_is_manual = models.BooleanField(
        default=False,
        help_text='When set, priority changes do not recalculate due_at.',
    )

    class Meta:
        db_table = 'tickets_ticket'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['submitter']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
            models.Index(fields=['due_at']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self) -> bool:
        from .sla_service import ticket_is_overdue

        return ticket_is_overdue(self)


class TicketAssignment(models.Model):
    """Assignment of a ticket to IT personnel (FR-18, FR-37)."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='assignments')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ticket_assignments',
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ticket_assignments_made',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_current = models.BooleanField(default=True)

    class Meta:
        db_table = 'tickets_ticketassignment'
        indexes = [
            models.Index(fields=['ticket']),
            models.Index(fields=['assigned_to']),
        ]

    def __str__(self):
        return f'{self.ticket_id} → {self.assigned_to}'


class TicketComment(models.Model):
    """Internal notes or comments on a ticket (FR-21)."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ticket_comments',
    )
    body = models.TextField()
    is_internal = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tickets_ticketcomment'
        ordering = ['created_at']

    def __str__(self):
        return f'Comment on #{self.ticket_id} by {self.author}'


class TicketStatusHistory(models.Model):
    """Record of ticket status changes (FR-36, FR-17)."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=50, blank=True)
    new_status = models.CharField(max_length=50)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ticket_status_changes',
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tickets_ticketstathistory'
        ordering = ['changed_at']
        indexes = [
            models.Index(fields=['ticket']),
            models.Index(fields=['changed_at']),
        ]

    def __str__(self):
        return f'{self.ticket_id}: {self.old_status} → {self.new_status}'


class TicketAttachment(models.Model):
    """Optional file uploaded when a ticket is created."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=ticket_attachment_upload_to)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='ticket_attachments_uploaded',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tickets_ticketattachment'
        ordering = ['uploaded_at']
        indexes = [
            models.Index(fields=['ticket', 'uploaded_at']),
        ]

    def __str__(self):
        return self.original_filename
