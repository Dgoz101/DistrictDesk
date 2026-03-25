"""
Class-based view mixins for role-based access (FR-5–FR-9).
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Require an authenticated user whose role is Administrator.

    Unauthenticated users are redirected to login (LoginRequiredMixin).
    Authenticated non-admins receive 403 Forbidden (UserPassesTestMixin).
    """

    raise_exception = True

    def test_func(self):
        return self.request.user.is_administrator
