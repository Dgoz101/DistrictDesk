"""
Production settings: DEBUG off, strict hosts, DB connection reuse, secure session.
Set DJANGO_ENV=production and provide DJANGO_SECRET_KEY and ALLOWED_HOSTS.
"""
from .base import *  # noqa: F401, F403
import os

DEBUG = False
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()]
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost']  # override with real host(s) in production

# DB connection reuse (use with PgBouncer or moderate worker count)
if 'default' in DATABASES and DATABASES['default']['ENGINE'] != 'django.db.backends.sqlite3':
    DATABASES['default']['CONN_MAX_AGE'] = 300

# Sessions in database so multiple app instances share session state
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
# Set these when behind HTTPS reverse proxy:
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
