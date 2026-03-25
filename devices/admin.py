from django.contrib import admin
from .models import Device, DeviceStatus, DeviceType


@admin.register(DeviceType)
class DeviceTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(DeviceStatus)
class DeviceStatusAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('asset_tag', 'device_type', 'model', 'status', 'assigned_user', 'location')
    list_filter = ('device_type', 'status')
    search_fields = ('asset_tag', 'model', 'serial_number')
