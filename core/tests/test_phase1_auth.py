"""Phase 1: registration, login, logout, password reset URL wiring."""
import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import resolve

from accounts.models import Role

User = get_user_model()


class Phase1AuthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Role.objects.get_or_create(name='Standard User')
        Role.objects.get_or_create(name='Administrator')

    def test_register_creates_user_with_standard_role(self):
        response = self.client.post(
            '/accounts/register/',
            {
                'email': 'newuser@example.com',
                'password1': 'complex-pass-123',
                'password2': 'complex-pass-123',
            },
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/accounts/login/')
        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.username, 'newuser@example.com')
        self.assertTrue(user.check_password('complex-pass-123'))
        self.assertEqual(user.role.name, 'Standard User')

    def test_login_and_logout(self):
        user = User.objects.create_user(
            username='u@example.com',
            email='u@example.com',
            password='testpass123',
        )
        role, _ = Role.objects.get_or_create(name='Standard User')
        user.role = role
        user.save()

        login = self.client.post(
            '/accounts/login/',
            {'username': 'u@example.com', 'password': 'testpass123'},
            follow=False,
        )
        self.assertEqual(login.status_code, 302)

        out = self.client.post('/accounts/logout/', follow=False)
        self.assertEqual(out.status_code, 302)

    def test_password_reset_url_resolves(self):
        match = resolve('/accounts/password-reset/')
        self.assertEqual(match.namespace, 'accounts')
        self.assertEqual(match.url_name, 'password_reset')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class Phase1PasswordResetFlowTests(TestCase):
    """FR-4: password reset sends a verifiable email with a secure reset link."""

    @classmethod
    def setUpTestData(cls):
        Role.objects.get_or_create(name='Standard User')
        Role.objects.get_or_create(name='Administrator')

    def setUp(self):
        self.user = User.objects.create_user(
            username='resetflow@example.com',
            email='resetflow@example.com',
            password='Old-password-123',
        )

    def test_password_reset_request_sends_email_with_reset_link(self):
        response = self.client.post(
            '/accounts/password-reset/',
            {'email': 'resetflow@example.com'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['resetflow@example.com'])
        self.assertIn('/accounts/reset/', msg.body)

    def test_password_reset_confirm_and_login_with_new_password(self):
        self.client.post(
            '/accounts/password-reset/',
            {'email': 'resetflow@example.com'},
        )
        body = mail.outbox[0].body
        match = re.search(r'/accounts/reset/([^/\s]+)/([^/\s]+)/', body)
        self.assertIsNotNone(match, msg=body)
        uidb64, token = match.group(1), match.group(2)
        # Django 5+ stores the token in session and redirects to .../set-password/
        # so the reset link is not leaked via Referer.
        get = self.client.get(f'/accounts/reset/{uidb64}/{token}/', follow=True)
        self.assertEqual(get.status_code, 200)
        post = self.client.post(
            f'/accounts/reset/{uidb64}/set-password/',
            {
                'new_password1': 'New-complex-pass-999',
                'new_password2': 'New-complex-pass-999',
            },
        )
        self.assertEqual(post.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('New-complex-pass-999'))
        login = self.client.post(
            '/accounts/login/',
            {
                'username': 'resetflow@example.com',
                'password': 'New-complex-pass-999',
            },
        )
        self.assertEqual(login.status_code, 302)
