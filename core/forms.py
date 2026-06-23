from django import forms

from .models import Location


class LocationForm(forms.ModelForm):
    """Administrator: building or room used on tickets and devices."""

    class Meta:
        model = Location
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'maxlength': 200, 'placeholder': 'e.g. Main Office — Room 204'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional notes'}),
        }
