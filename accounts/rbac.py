"""
RBAC role constants and helpers.
"""

ROLE_NAME_ADMINISTRATOR = 'Administrator'
ROLE_NAME_STANDARD_USER = 'Standard User'


def user_has_role(user, *allowed_role_names):
    """
    Return True when user's role name matches one of allowed names.
    """
    if not getattr(user, 'is_authenticated', False):
        return False
    role = getattr(user, 'role', None)
    if not role or not role.name:
        return False
    allowed = {name.lower() for name in allowed_role_names}
    return role.name.lower() in allowed


def user_is_administrator(user):
    """Return True when user has Administrator role."""
    return user_has_role(user, ROLE_NAME_ADMINISTRATOR)


def user_is_standard_user(user):
    """
    Return True for standard users and users without a role.

    Existing app behavior treats missing role as standard.
    """
    if not getattr(user, 'is_authenticated', False):
        return False
    role = getattr(user, 'role', None)
    if not role or not role.name:
        return True
    return role.name.lower() in {
        ROLE_NAME_STANDARD_USER.lower(),
        'standard',
    }
