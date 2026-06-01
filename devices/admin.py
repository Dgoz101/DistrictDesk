from django.contrib import admin

from .models import (
    Device,
    DeviceCheckout,
    DeviceCheckoutPolicy,
    DeviceFine,
    DeviceFineType,
    DeviceStatus,
    DeviceType,
)


@admin.register(DeviceType)
class DeviceTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(DeviceStatus)
class DeviceStatusAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        'asset_tag',
        'device_type',
        'model',
        'status',
        'warranty_end_date',
        'assigned_user',
        'location',
    )
    list_filter = ('device_type', 'status')
    search_fields = ('asset_tag', 'model', 'serial_number')


@admin.register(DeviceCheckoutPolicy)
class DeviceCheckoutPolicyAdmin(admin.ModelAdmin):
    list_display = ('late_fee_enabled', 'late_fee_per_day', 'late_grace_days', 'late_fee_max_amount')


@admin.register(DeviceFineType)
class DeviceFineTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'default_amount', 'sort_order', 'is_active', 'is_system')
    list_filter = ('is_active',)


@admin.register(DeviceFine)
class DeviceFineAdmin(admin.ModelAdmin):
    list_display = ('description', 'checkout', 'amount', 'quantity', 'status', 'is_late_fee', 'assessed_at')
    list_filter = ('status', 'is_late_fee')


class DeviceFineInline(admin.TabularInline):
    model = DeviceFine
    extra = 0


@admin.register(DeviceCheckout)
class DeviceCheckoutAdmin(admin.ModelAdmin):
    list_display = ('device', 'checked_out_to', 'checked_out_at', 'due_at', 'returned_at')
    inlines = [DeviceFineInline]
