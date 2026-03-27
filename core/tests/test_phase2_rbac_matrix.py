"""Phase 2 RBAC: URL matrix and template nav guards (complements test_phase2_rbac unit tests)."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Role

User = get_user_model()


class Phase2RBACMatrixTests(TestCase):
    """Assert admin-only routes return expected status codes; nav omits admin links for standard users."""

    @classmethod
    def setUpTestData(cls):
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')

    def setUp(self):
        self.std = User.objects.create_user(
            username='rbac_std@example.com',
            email='rbac_std@example.com',
            password='pass12345',
        )
        self.std.role = self.role_std
        self.std.save()
        self.adm = User.objects.create_user(
            username='rbac_adm@example.com',
            email='rbac_adm@example.com',
            password='pass12345',
        )
        self.adm.role = self.role_admin
        self.adm.save()

    def test_anonymous_admin_routes_redirect_to_login(self):
        for path in (
            '/dashboard/',
            '/dashboard/api/summary/',
            '/devices/',
            '/accounts/users/',
            '/tickets/settings/',
        ):
            with self.subTest(path=path):
                r = self.client.get(path)
                self.assertEqual(r.status_code, 302, msg=path)
                self.assertIn('/accounts/login/', r['Location'])

    def test_standard_user_gets_403_on_admin_only_routes(self):
        self.client.login(username='rbac_std@example.com', password='pass12345')
        for path in (
            '/dashboard/',
            '/dashboard/api/summary/',
            '/devices/',
            '/accounts/users/',
            '/tickets/settings/',
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403, msg=path)

    def test_administrator_gets_200_on_admin_html_routes(self):
        self.client.login(username='rbac_adm@example.com', password='pass12345')
        for path in (
            '/dashboard/',
            '/devices/',
            '/accounts/users/',
            '/tickets/settings/',
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200, msg=path)

    def test_administrator_api_summary_json(self):
        self.client.login(username='rbac_adm@example.com', password='pass12345')
        r = self.client.get('/dashboard/api/summary/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'].split(';')[0], 'application/json')

    def test_standard_user_tickets_list_200(self):
        self.client.login(username='rbac_std@example.com', password='pass12345')
        r = self.client.get('/tickets/')
        self.assertEqual(r.status_code, 200)

    def test_nav_bar_standard_user_has_no_admin_links(self):
        self.client.login(username='rbac_std@example.com', password='pass12345')
        r = self.client.get('/tickets/')
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'href="/dashboard/"')
        self.assertNotContains(r, 'href="/devices/"')
        self.assertNotContains(r, 'href="/accounts/users/"')
        self.assertNotContains(r, 'href="/tickets/settings/"')

    def test_nav_bar_administrator_has_admin_links(self):
        self.client.login(username='rbac_adm@example.com', password='pass12345')
        r = self.client.get('/tickets/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'href="/dashboard/"')
        self.assertContains(r, 'href="/devices/"')
        self.assertContains(r, 'href="/accounts/users/"')
        self.assertContains(r, 'href="/tickets/settings/"')
