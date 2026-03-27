"""
Production settings: DEBUG off, fail-fast secret key and hosts, HTTPS-oriented defaults.

Required environment variables:
  DJANGO_SECRET_KEY — non-empty, must not be the development placeholder.
  DJANGO_ALLOWED_HOSTS — comma-separated hostnames (no empty production deploy).

Set DJANGO_ENV=production. When behind a TLS-terminating reverse proxy, ensure
X-Forwarded-Proto is set to https so SECURE_PROXY_SSL_HEADER works.
"""
from .base import *  # noqa: F401, F403
import os

from django.core.exceptions import ImproperlyConfigured

DEBUG = False

# Must match the insecure fallback string in base.py (rejected in production).
_INSECURE_SECRET_KEY = 'django-insecure-change-me-in-production'

_secret = os.environ.get('DJANGO_SECRET_KEY', '').strip()
if not _secret or _secret == _INSECURE_SECRET_KEY:
    raise ImproperlyConfigured(
        'Set DJANGO_SECRET_KEY to a strong, unique value in production. '
        'It must not be empty and must not use the development placeholder.'
    )
SECRET_KEY = _secret

_hosts_raw = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _hosts_raw.split(',') if h.strip()]
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        'Set DJANGO_ALLOWED_HOSTS to a comma-separated list of hostnames '
        '(e.g. app.example.com,www.example.com).'
    )

# DB connection reuse (use with PgBouncer or moderate worker count)
if 'default' in DATABASES and DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
    DATABASES['default']['CONN_MAX_AGE'] = 300

# Sessions in database so multiple app instances share session state
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Security (HTTPS)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
