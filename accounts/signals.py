"""Authentication audit hooks (login success/failure, logout)."""
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed

from core.audit import log_auth_login, log_auth_logout


def _on_user_logged_in(sender, request, user, **kwargs):
    log_auth_login(user=user, request=request, success=True)


def _on_user_login_failed(sender, credentials, request, **kwargs):
    identifier = ''
    if credentials:
        identifier = credentials.get('username') or credentials.get('email') or ''
    log_auth_login(user=None, request=request, success=False, identifier=identifier)


def _on_user_logged_out(sender, request, user, **kwargs):
    log_auth_logout(user=user, request=request)


def connect_auth_audit_signals():
    user_logged_in.connect(_on_user_logged_in, dispatch_uid='districtdesk_audit_login_success')
    user_login_failed.connect(_on_user_login_failed, dispatch_uid='districtdesk_audit_login_failed')
    user_logged_out.connect(_on_user_logged_out, dispatch_uid='districtdesk_audit_logout')
