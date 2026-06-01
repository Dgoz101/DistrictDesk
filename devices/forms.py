from django import forms
from django.contrib.auth import get_user_model
from core.models import Location

from .models import Device, DeviceCheckoutPolicy, DeviceFineType, DeviceStatus, DeviceType

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


class DeviceFineTypeForm(forms.ModelForm):
    class Meta:
        model = DeviceFineType
        fields = ['name', 'description', 'default_amount', 'sort_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'maxlength': 100}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'default_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'sort_order': forms.NumberInput(attrs={'step': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.is_system:
            self.fields['name'].disabled = True


class DeviceCheckoutPolicyForm(forms.ModelForm):
    class Meta:
        model = DeviceCheckoutPolicy
        fields = [
            'late_fee_enabled',
            'late_fee_per_day',
            'late_grace_days',
            'late_fee_max_amount',
        ]
        widgets = {
            'late_fee_per_day': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'late_grace_days': forms.NumberInput(attrs={'step': '1', 'min': '0'}),
            'late_fee_max_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def clean_late_fee_max_amount(self):
        val = self.cleaned_data.get('late_fee_max_amount')
        if val is not None and val <= 0:
            return None
        return val


class AddCheckoutFinesForm(forms.Form):
    """Post-return: add additional damage fines to a closed checkout."""

    custom_fine_description = forms.CharField(max_length=200, required=False, label='Description')
    custom_fine_amount = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
        required=False,
        label='Amount',
    )
    custom_fine_notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)
