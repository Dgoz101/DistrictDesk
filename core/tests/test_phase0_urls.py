"""
Smoke tests for Phase 0: routing, health check, auth redirects, role-based redirects.
"""
import json
import sys
import unittest

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from accounts.models import Role

User = get_user_model()

# Django 4.2 test client fails copying template context on Python 3.14+ (AttributeError on Context.__copy__).
_PY314_TEMPLATE_TEST_SKIP = sys.version_info >= (3, 14)


class Phase0URLTests(TestCase):
    """URLs, templates, and redirects introduced in Phase 0."""

    @classmethod
    def setUpTestData(cls):
        cls.role_admin = Role.objects.create(name='Administrator')
        cls.role_standard = Role.objects.create(name='Standard User')

    def setUp(self):
        self.client = Client()

    def test_health_returns_ok_json(self):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode())
        self.assertEqual(data.get('status'), 'ok')

    def test_home_redirects_anonymous_to_login(self):
        response = self.client.get('/')
        self.assertRedirects(
            response,
            '/accounts/login/',
            fetch_redirect_response=False,
            status_code=302,
        )

    @unittest.skipIf(
        _PY314_TEMPLATE_TEST_SKIP,
        'Django 4.2 test client + Python 3.14+: template context copy error; use Python 3.12-3.13 for full HTML tests.',
    )
    def test_login_placeholder_renders(self):
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign in')

    def test_tickets_requires_login(self):
        response = self.client.get('/tickets/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_devices_requires_admin(self):
        user = User.objects.create_user(
            username='standard1',
            email='standard1@example.com',
            password='testpass123',
        )
        user.role = self.role_standard
        user.save()
        self.client.login(username='standard1', password='testpass123')
        response = self.client.get('/devices/')
        self.assertEqual(response.status_code, 403)

    def test_dashboard_requires_admin(self):
        user = User.objects.create_user(
            username='standard2',
            email='standard2@example.com',
            password='testpass123',
        )
        user.role = self.role_standard
        user.save()
        self.client.login(username='standard2', password='testpass123')
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 403)

    def test_home_redirects_admin_to_dashboard(self):
        admin = User.objects.create_user(
            username='admin1',
            email='admin1@example.com',
            password='testpass123',
        )
        admin.role = self.role_admin
        admin.save()
        self.client.login(username='admin1', password='testpass123')
        response = self.client.get('/')
        self.assertRedirects(
            response,
            '/dashboard/',
            fetch_redirect_response=False,
            status_code=302,
        )

    def test_home_redirects_standard_user_to_tickets(self):
        user = User.objects.create_user(
            username='standard3',
            email='standard3@example.com',
            password='testpass123',
        )
        user.role = self.role_standard
        user.save()
        self.client.login(username='standard3', password='testpass123')
        response = self.client.get('/')
        self.assertRedirects(
            response,
            '/tickets/',
            fetch_redirect_response=False,
            status_code=302,
        )

    @unittest.skipIf(
        _PY314_TEMPLATE_TEST_SKIP,
        'Django 4.2 test client + Python 3.14+: template context copy error; use Python 3.12-3.13 for full HTML tests.',
    )
    def test_tickets_placeholder_authenticated(self):
        user = User.objects.create_user(
            username='standard4',
            email='standard4@example.com',
            password='testpass123',
        )
        user.role = self.role_standard
        user.save()
        self.client.login(username='standard4', password='testpass123')
        response = self.client.get('/tickets/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tickets')
