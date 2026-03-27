"""Production settings fail-fast and HTTPS defaults (isolated subprocess per case)."""

import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parent.parent.parent

_SETUP_SCRIPT = """
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
"""


def _run_django_setup(env_updates, pop_keys=None):
    env = dict(os.environ)
    env['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    env['PYTHONPATH'] = str(ROOT)
    env.setdefault('DJANGO_USE_SQLITE', '1')
    if pop_keys:
        for key in pop_keys:
            env.pop(key, None)
    env.update(env_updates)
    return subprocess.run(
        [sys.executable, '-c', _SETUP_SCRIPT],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


class ProductionSettingsTests(SimpleTestCase):
    _valid_secret = 'a' * 50
    _valid_hosts = 'app.example.com'

    def test_production_settings_load_with_required_env(self):
        r = _run_django_setup(
            {
                'DJANGO_ENV': 'production',
                'DJANGO_SECRET_KEY': self._valid_secret,
                'DJANGO_ALLOWED_HOSTS': self._valid_hosts,
            }
        )
        self.assertEqual(r.returncode, 0, msg=r.stderr + r.stdout)

    def test_production_missing_secret_key_fails(self):
        r = _run_django_setup(
            {
                'DJANGO_ENV': 'production',
                'DJANGO_ALLOWED_HOSTS': self._valid_hosts,
            },
            pop_keys=['DJANGO_SECRET_KEY'],
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('DJANGO_SECRET_KEY', r.stderr + r.stdout)

    def test_production_insecure_placeholder_secret_fails(self):
        r = _run_django_setup(
            {
                'DJANGO_ENV': 'production',
                'DJANGO_SECRET_KEY': 'django-insecure-change-me-in-production',
                'DJANGO_ALLOWED_HOSTS': self._valid_hosts,
            }
        )
        self.assertNotEqual(r.returncode, 0)

    def test_production_empty_allowed_hosts_fails(self):
        r = _run_django_setup(
            {
                'DJANGO_ENV': 'production',
                'DJANGO_SECRET_KEY': self._valid_secret,
                'DJANGO_ALLOWED_HOSTS': '',
            }
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('DJANGO_ALLOWED_HOSTS', r.stderr + r.stdout)

    def test_production_https_flags_enabled(self):
        r = _run_django_setup(
            {
                'DJANGO_ENV': 'production',
                'DJANGO_SECRET_KEY': self._valid_secret,
                'DJANGO_ALLOWED_HOSTS': self._valid_hosts,
            }
        )
        self.assertEqual(r.returncode, 0)
        check = subprocess.run(
            [
                sys.executable,
                '-c',
                'import os, django; os.environ.setdefault("DJANGO_SETTINGS_MODULE","config.settings"); '
                'django.setup(); from django.conf import settings; '
                'assert settings.SESSION_COOKIE_SECURE is True; '
                'assert settings.CSRF_COOKIE_SECURE is True; '
                'assert settings.SECURE_SSL_REDIRECT is True; '
                'assert settings.SECURE_HSTS_SECONDS == 31536000',
            ],
            cwd=str(ROOT),
            env={
                **os.environ,
                'PYTHONPATH': str(ROOT),
                'DJANGO_SETTINGS_MODULE': 'config.settings',
                'DJANGO_ENV': 'production',
                'DJANGO_SECRET_KEY': self._valid_secret,
                'DJANGO_ALLOWED_HOSTS': self._valid_hosts,
                'DJANGO_USE_SQLITE': '1',
            },
            capture_output=True,
            text=True,
        )
        self.assertEqual(check.returncode, 0, msg=check.stderr + check.stdout)
