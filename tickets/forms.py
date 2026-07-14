from django import forms
from django.contrib.auth import get_user_model

from core.models import Location
from devices.models import Device

from .models import CannedResponse, PriorityLevel, Ticket, TicketCategory, TicketRelation

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
    """Administrator: status, priority, category, optional manual due date (FR-19–FR-20)."""

    class Meta:
        model = Ticket
        fields = ['status', 'priority', 'category', 'due_at']
        widgets = {
            'due_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_at'].required = False
        self.fields['due_at'].help_text = (
            'Leave blank to use priority SLA on new tickets; clear to remove a manual date.'
        )


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
        fields = ['name', 'sort_order', 'due_days']
        widgets = {
            'name': forms.TextInput(attrs={'maxlength': 50}),
        }


class CannedResponseForm(forms.ModelForm):
    """Administrator: reusable comment snippet."""

    class Meta:
        model = CannedResponse
        fields = ['title', 'body', 'sort_order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'maxlength': 100}),
            'body': forms.Textarea(attrs={'rows': 6}),
        }


class TicketCommentForm(forms.Form):
    """Internal or visible comment (FR-21)."""

    body = forms.CharField(
        label='Comment',
        widget=forms.Textarea(attrs={'rows': 4, 'id': 'ticket-comment-body'}),
    )
    is_internal = forms.BooleanField(
        label='Internal note (hidden from requester)',
        initial=True,
        required=False,
    )


class TicketRelationForm(forms.Form):
    """Administrator: link this ticket to another by ID."""

    related_ticket_id = forms.IntegerField(
        label='Ticket ID',
        min_value=1,
        widget=forms.NumberInput(attrs={'placeholder': 'e.g. 42', 'min': 1}),
    )
    relation_type = forms.ChoiceField(
        label='Relationship',
        choices=TicketRelation.RelationType.choices,
        initial=TicketRelation.RelationType.RELATED,
    )
    note = forms.CharField(
        label='Note',
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Optional'}),
    )

    def __init__(self, *args, source_ticket=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_ticket = source_ticket

    def clean_related_ticket_id(self):
        pk = self.cleaned_data['related_ticket_id']
        if self.source_ticket and pk == self.source_ticket.pk:
            raise forms.ValidationError('Cannot link a ticket to itself.')
        other = Ticket.objects.filter(pk=pk).first()
        if other is None:
            raise forms.ValidationError('No ticket found with that ID.')
        self.cleaned_data['_related_ticket'] = other
        return pk

    def clean(self):
        cleaned = super().clean()
        other = cleaned.get('_related_ticket')
        if other is None and 'related_ticket_id' in cleaned:
            # clean_related_ticket_id already ran; reload if needed
            other = Ticket.objects.filter(pk=cleaned['related_ticket_id']).first()
            cleaned['_related_ticket'] = other
        return cleaned
