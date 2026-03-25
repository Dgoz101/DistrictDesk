from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q

from .models import Role, User


class EmailLoginForm(AuthenticationForm):
    """Log in with email; stored as username for compatibility with Django auth."""

    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}),
    )


class RegisterForm(forms.ModelForm):
    """Create account with email + password (FR-1); assigns Standard User role."""

    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    class Meta:
        model = User
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password1') and cleaned.get('password2'):
            if cleaned['password1'] != cleaned['password2']:
                raise forms.ValidationError('The two password fields do not match.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data['email']
        user.username = email
        user.email = email
        user.set_password(self.cleaned_data['password1'])
        role, _ = Role.objects.get_or_create(name='Standard User')
        user.role = role
        if commit:
            user.save()
        return user


class UserAdminForm(forms.ModelForm):
    """Administrator: adjust role and active flag (FR-38). Password changes use Django admin or reset flow."""

    class Meta:
        model = User
        fields = ['role', 'is_active']

    def __init__(self, *args, current_user=None, **kwargs):
        self.current_user = current_user
        super().__init__(*args, **kwargs)
        self.fields['role'].queryset = Role.objects.order_by('name')
        self.fields['role'].required = False

    def clean(self):
        cleaned = super().clean()
        if self.current_user and self.instance.pk == self.current_user.pk:
            if cleaned.get('is_active') is False:
                raise forms.ValidationError(
                    {'is_active': ['You cannot deactivate your own account.']}
                )
        return cleaned
