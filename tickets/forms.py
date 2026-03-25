from django import forms
from django.contrib.auth import get_user_model

from core.models import Location
from devices.models import Device

from .models import PriorityLevel, Ticket, TicketCategory

User = get_user_model()


class TicketForm(forms.ModelForm):
    """New ticket (FR-10–FR-13). Submitter and status are set in the view."""

    class Meta:
        model = Ticket
        fields = [
            'title',
            'description',
            'category',
            'priority',
            'device',
            'location',
            'contact_info',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'maxlength': 200}),
            'description': forms.Textarea(attrs={'rows': 6}),
            'contact_info': forms.TextInput(
                attrs={'placeholder': 'Optional phone, extension, or room'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['device'].queryset = Device.objects.select_related(
            'device_type', 'status'
        ).order_by('asset_tag')
        self.fields['device'].required = False
        self.fields['location'].queryset = Location.objects.order_by('name')
        self.fields['location'].required = False
        self.fields['category'].empty_label = None
        self.fields['priority'].empty_label = None


class TicketAdminUpdateForm(forms.ModelForm):
    """Administrator: status, priority, category (FR-19–FR-20)."""

    class Meta:
        model = Ticket
        fields = ['status', 'priority', 'category']


class TicketAssignForm(forms.Form):
    """Assign ticket to an active user (FR-18)."""

    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='Assign to',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True).order_by(
            'username'
        )


class TicketCategoryForm(forms.ModelForm):
    """Administrator: ticket category lookup (FR-39)."""

    class Meta:
        model = TicketCategory
        fields = ['name', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'maxlength': 100}),
        }


class PriorityLevelForm(forms.ModelForm):
    """Administrator: priority level lookup (FR-39)."""

    class Meta:
        model = PriorityLevel
        fields = ['name', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={'maxlength': 50}),
        }


class TicketCommentForm(forms.Form):
    """Internal or visible comment (FR-21)."""

    body = forms.CharField(
        label='Comment',
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    is_internal = forms.BooleanField(
        label='Internal note (hidden from requester)',
        initial=True,
        required=False,
    )
