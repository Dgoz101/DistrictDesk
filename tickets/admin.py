from django.contrib import admin
from .models import (
    CannedResponse,
    PriorityLevel,
    Ticket,
    TicketAssignment,
    TicketAttachment,
    TicketCategory,
    TicketComment,
    TicketRelation,
    TicketStatusHistory,
)


@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'sort_order')


@admin.register(PriorityLevel)
class PriorityLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'sort_order', 'due_days')


@admin.register(CannedResponse)
class CannedResponseAdmin(admin.ModelAdmin):
    list_display = ('title', 'sort_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'body')


@admin.register(TicketRelation)
class TicketRelationAdmin(admin.ModelAdmin):
    list_display = ('ticket_low', 'ticket_high', 'relation_type', 'created_by', 'created_at')
    list_filter = ('relation_type',)


class TicketAssignmentInline(admin.TabularInline):
    model = TicketAssignment
    extra = 0


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0


class TicketStatusHistoryInline(admin.TabularInline):
    model = TicketStatusHistory
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'changed_by', 'changed_at')


class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    readonly_fields = ('original_filename', 'size_bytes', 'content_type', 'uploaded_by', 'uploaded_at')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('title', 'submitter', 'category', 'priority', 'status', 'due_at', 'created_at')
    list_filter = ('status', 'category', 'priority')
    search_fields = ('title', 'description')
    inlines = [
        TicketAssignmentInline,
        TicketCommentInline,
        TicketAttachmentInline,
        TicketStatusHistoryInline,
    ]


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'ticket', 'size_bytes', 'uploaded_by', 'uploaded_at')
    list_filter = ('uploaded_at',)


@admin.register(TicketAssignment)
class TicketAssignmentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'assigned_to', 'assigned_by', 'assigned_at', 'is_current')


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'is_internal', 'created_at')


@admin.register(TicketStatusHistory)
class TicketStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'old_status', 'new_status', 'changed_by', 'changed_at')
