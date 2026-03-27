"""
Class-based view mixins for role-based access (FR-5–FR-9).
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .rbac import ROLE_NAME_ADMINISTRATOR, user_has_role


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Require an authenticated user with one of the allowed roles.
    """

    raise_exception = True
    allowed_roles = ()

    def test_func(self):
        return user_has_role(self.request.user, *self.allowed_roles)


class AdminRequiredMixin(RoleRequiredMixin):
    """
    Require an authenticated user whose role is Administrator.

    Unauthenticated users are redirected to login (LoginRequiredMixin).
    Authenticated non-admins receive 403 Forbidden (UserPassesTestMixin).
    """
    allowed_roles = (ROLE_NAME_ADMINISTRATOR,)
