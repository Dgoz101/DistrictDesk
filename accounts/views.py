from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, ListView, UpdateView

from accounts.mixins import AdminRequiredMixin

from .forms import EmailLoginForm, RegisterForm, UserAdminForm

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
        messages.success(self.request, 'User updated.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('accounts:user_list')
