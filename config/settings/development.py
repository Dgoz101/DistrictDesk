"""
Development settings: DEBUG on, permissive hosts, no connection pooling.
"""
from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# Print password-reset and other mail to the console during development (FR-4).
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Optional: add dev host from env
import os
_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS')
if _hosts:
    ALLOWED_HOSTS = [h.strip() for h in _hosts.split(',')]

# Development: short-lived DB connections
if 'default' in DATABASES and DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
    DATABASES['default']['CONN_MAX_AGE'] = 0
