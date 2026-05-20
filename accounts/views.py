from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, ListView, UpdateView

from accounts.mixins import AdminRequiredMixin
from core.audit import log_user_admin_update
from core.models import AdminAuditEntry

from .forms import EmailLoginForm, RegisterForm, UserAdminForm, UserEmailPreferencesForm

User = get_user_model()


class DistrictDeskLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = EmailLoginForm
    redirect_authenticated_user = True


class DistrictDeskLogoutView(LogoutView):
    next_page = reverse_lazy('home')


class RegisterView(FormView):
    template_name = 'accounts/register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            'Your account was created. You can sign in now.',
        )
        return super().form_valid(form)


class UserEmailPreferencesView(LoginRequiredMixin, FormView):
    """Allow any signed-in user to toggle ticket update emails."""

    form_class = UserEmailPreferencesForm
    template_name = 'accounts/email_preferences.html'
    success_url = reverse_lazy('accounts:email_preferences')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Your email preferences were saved.')
        return super().form_valid(form)


class UserListView(AdminRequiredMixin, ListView):
    """List users for administrators (FR-38)."""
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 25

    def get_queryset(self):
        return User.objects.select_related('role').order_by('-date_joined', 'username')


class UserAdminUpdateView(AdminRequiredMixin, UpdateView):
    """Edit role and active status (FR-38)."""
    model = User
    form_class = UserAdminForm
    template_name = 'accounts/user_form.html'
    context_object_name = 'edit_user'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['current_user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.get_object()
        old_role_name = user.role.name if user.role_id else ''
        old_active = user.is_active
        response = super().form_valid(form)
        user.refresh_from_db()
        new_role_name = user.role.name if user.role_id else ''
        log_user_admin_update(
            self.request.user,
            user,
            old_role_name=old_role_name,
            new_role_name=new_role_name,
            old_active=old_active,
            new_active=user.is_active,
        )
        messages.success(self.request, 'User updated.')
        return response

    def get_success_url(self):
        return reverse_lazy('accounts:user_list')


class AdminAuditListView(AdminRequiredMixin, ListView):
    """Administrator audit log (roles, lookups, sensitive ticket field changes)."""

    model = AdminAuditEntry
    template_name = 'accounts/audit_list.html'
    context_object_name = 'entries'
    paginate_by = 50

    def get_queryset(self):
        qs = AdminAuditEntry.objects.select_related('actor', 'ticket').order_by('-created_at')
        entity = self.request.GET.get('entity_type', '').strip()
        if entity and entity in dict(AdminAuditEntry.EntityType.choices):
            qs = qs.filter(entity_type=entity)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['entity_type'] = self.request.GET.get('entity_type', '').strip()
        ctx['entity_type_choices'] = AdminAuditEntry.EntityType.choices
        get = self.request.GET.copy()
        if 'page' in get:
            del get['page']
        ctx['filter_query'] = get.urlencode()
        return ctx
