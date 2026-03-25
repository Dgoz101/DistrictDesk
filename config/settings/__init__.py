"""
Load the appropriate settings module based on DJANGO_ENV.
Default: development. Set DJANGO_ENV=production for production.
"""
import os

_env = os.environ.get('DJANGO_ENV', 'development').lower()

if _env == 'production':
    from .production import *  # noqa: F401, F403
else:
    from .development import *  # noqa: F401, F403
