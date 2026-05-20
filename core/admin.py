from django.contrib import admin

from .models import AdminAuditEntry, Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(AdminAuditEntry)
class AdminAuditEntryAdmin(admin.ModelAdmin):
    list_display = (
        'created_at',
        'actor',
        'action',
        'entity_type',
        'object_label',
        'field_name',
    )
    list_filter = ('action', 'entity_type', 'created_at')
    search_fields = ('object_label', 'old_value', 'new_value', 'actor__username', 'actor__email')
    readonly_fields = (
        'action',
        'entity_type',
        'object_id',
        'object_label',
        'field_name',
        'old_value',
        'new_value',
        'actor',
        'ticket',
        'created_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
