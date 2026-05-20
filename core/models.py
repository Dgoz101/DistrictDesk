from django.conf import settings
from django.db import models


class Location(models.Model):
    """Shared location for tickets (optional) and device assignment (FR-12, FR-29)."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'core_location'

    def __str__(self):
        return self.name


class AdminAuditEntry(models.Model):
    """Append-only log of administrator changes, authentication events, and related edits."""

    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'

    class EntityType(models.TextChoices):
        USER = 'user', 'User'
        AUTH = 'auth', 'Authentication'
        TICKET_CATEGORY = 'ticket_category', 'Ticket category'
        PRIORITY_LEVEL = 'priority_level', 'Priority level'
        TICKET = 'ticket', 'Ticket'

    action = models.CharField(max_length=10, choices=Action.choices)
    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    object_label = models.CharField(max_length=255)
    field_name = models.CharField(max_length=50, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='admin_audit_entries',
    )
    ticket = models.ForeignKey(
        'tickets.Ticket',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='audit_entries',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_adminauditentry'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entity_type', 'object_id']),
            models.Index(fields=['actor', 'created_at']),
            models.Index(fields=['ticket', 'created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        if self.field_name:
            return f'{self.entity_type} #{self.object_id} {self.field_name}'
        return f'{self.action} {self.entity_type} {self.object_label}'
