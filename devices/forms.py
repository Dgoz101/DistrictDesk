from django import forms
from django.contrib.auth import get_user_model

from core.models import Location

from .models import Device, DeviceStatus, DeviceType

User = get_user_model()


class DeviceForm(forms.ModelForm):
    """Device inventory (FR-26–FR-29)."""

    class Meta:
        model = Device
        fields = [
            'asset_tag',
            'device_type',
            'model',
            'serial_number',
            'status',
            'assigned_user',
            'location',
        ]
        widgets = {
            'asset_tag': forms.TextInput(attrs={'maxlength': 50}),
            'model': forms.TextInput(attrs={'maxlength': 150}),
            'serial_number': forms.TextInput(attrs={'maxlength': 100}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['device_type'].queryset = DeviceType.objects.order_by('name')
        self.fields['device_type'].empty_label = None
        self.fields['status'].queryset = DeviceStatus.objects.order_by('name')
        self.fields['status'].empty_label = None
        self.fields['location'].queryset = Location.objects.order_by('name')
        self.fields['location'].required = False
        self.fields['location'].empty_label = '—'
        self.fields['assigned_user'].queryset = User.objects.filter(is_active=True).order_by(
            'username'
        )
        self.fields['assigned_user'].required = False
        self.fields['assigned_user'].empty_label = '—'
