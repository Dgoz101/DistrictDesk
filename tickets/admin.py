from django.contrib import admin
from .models import (
    PriorityLevel,
    Ticket,
    TicketAssignment,
    TicketCategory,
    TicketComment,
    TicketStatusHistory,
)


@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'sort_order')


@admin.register(PriorityLevel)
class PriorityLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'sort_order')


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


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('title', 'submitter', 'category', 'priority', 'status', 'created_at')
    list_filter = ('status', 'category', 'priority')
    search_fields = ('title', 'description')
    inlines = [TicketAssignmentInline, TicketCommentInline, TicketStatusHistoryInline]


@admin.register(TicketAssignment)
class TicketAssignmentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'assigned_to', 'assigned_by', 'assigned_at', 'is_current')


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'is_internal', 'created_at')


@admin.register(TicketStatusHistory)
class TicketStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'old_status', 'new_status', 'changed_by', 'changed_at')
