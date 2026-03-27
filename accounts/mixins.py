"""
Class-based view mixins for role-based access (FR-5–FR-9).
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import resolve_url

from .rbac import ROLE_NAME_ADMINISTRATOR, user_has_role


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Require an authenticated user with one of the allowed roles.
    """

    raise_exception = True
    allowed_roles = ()

    def test_func(self):
        return user_has_role(self.request.user, *self.allowed_roles)

    def handle_no_permission(self):
        """
        With raise_exception=True, Django's AccessMixin would return 403 for
        anonymous users. Redirect unauthenticated users to login; keep 403 for
        authenticated users who fail the role test.
        """
        if not self.request.user.is_authenticated:
            path = self.request.get_full_path()
            return redirect_to_login(
                path,
                resolve_url(self.get_login_url()),
                self.get_redirect_field_name(),
            )
        if self.raise_exception:
            raise PermissionDenied(self.get_permission_denied_message())
        return super().handle_no_permission()


class AdminRequiredMixin(RoleRequiredMixin):
    """
    Require an authenticated user whose role is Administrator.

    Unauthenticated users are redirected to login (LoginRequiredMixin).
    Authenticated non-admins receive 403 Forbidden (UserPassesTestMixin).
    """
    allowed_roles = (ROLE_NAME_ADMINISTRATOR,)
