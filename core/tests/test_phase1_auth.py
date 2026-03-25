"""Phase 1: registration, login, logout, password reset URL wiring."""
from django.contrib.auth import get_user_model
from django.test import TestCase
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
