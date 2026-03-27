"""
Function-view decorators for role-based access (FR-5–FR-9).
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .rbac import user_is_administrator


def admin_required(view_func):
    """
    Require an authenticated user whose role is Administrator.

    Anonymous users are redirected to the login page.
    Authenticated non-admins receive 403 Forbidden.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not user_is_administrator(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper
