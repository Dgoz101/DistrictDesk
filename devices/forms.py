from django import forms
from django.contrib.auth import get_user_model

from core.models import Location

from .models import Device, DeviceStatus, DeviceType

User = get_user_model()


class DeviceForm(forms.ModelForm):
    """Device inventory (FR-26–FR-29) plus warranty / purchase metadata."""

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
            'purchase_date',
            'warranty_end_date',
            'purchase_vendor',
            'purchase_order',
        ]
        widgets = {
            'asset_tag': forms.TextInput(attrs={'maxlength': 50}),
            'model': forms.TextInput(attrs={'maxlength': 150}),
            'serial_number': forms.TextInput(attrs={'maxlength': 100}),
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
            'warranty_end_date': forms.DateInput(attrs={'type': 'date'}),
            'purchase_vendor': forms.TextInput(attrs={'maxlength': 200}),
            'purchase_order': forms.TextInput(attrs={'maxlength': 100}),
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
        self.fields['assigned_user'].help_text = (
            'Long-term custodian / owner in inventory. Loaners use checkout on the device detail page.'
        )
        self.fields['purchase_date'].required = False
        self.fields['warranty_end_date'].required = False
        self.fields['purchase_vendor'].required = False
        self.fields['purchase_order'].required = False


class DeviceCheckoutForm(forms.Form):
    checked_out_to = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='Checked out to',
    )
    due_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
    )
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['checked_out_to'].queryset = User.objects.filter(is_active=True).order_by(
            'username'
        )
