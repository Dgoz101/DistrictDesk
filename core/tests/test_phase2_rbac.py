"""Phase 2: RBAC helpers (decorators + mixins)."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from accounts.decorators import admin_required
from accounts.mixins import AdminRequiredMixin, RoleRequiredMixin
from accounts.models import Role
from accounts.rbac import ROLE_NAME_ADMINISTRATOR, ROLE_NAME_STANDARD_USER, user_has_role

User = get_user_model()


@admin_required
def _sample_admin_view(request):
    return HttpResponse('ok')


class Phase2RBACTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')
        cls.role_standard, _ = Role.objects.get_or_create(name='Standard User')

    def test_admin_required_redirects_anonymous(self):
        factory = RequestFactory()
        request = factory.get('/sample/')
        request.user = AnonymousUser()
        response = _sample_admin_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_admin_required_allows_admin(self):
        factory = RequestFactory()
        user = User.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='x',
        )
        user.role = self.role_admin
        user.save()
        request = factory.get('/sample/')
        request.user = user
        response = _sample_admin_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')

    def test_admin_required_blocks_standard_user(self):
        factory = RequestFactory()
        user = User.objects.create_user(
            username='std@example.com',
            email='std@example.com',
            password='x',
        )
        user.role = self.role_standard
        user.save()
        request = factory.get('/sample/')
        request.user = user
        with self.assertRaises(PermissionDenied):
            _sample_admin_view(request)

    def test_admin_required_mixin_test_func(self):
        factory = RequestFactory()
        request = factory.get('/')
        user = User.objects.create_user(
            username='a@example.com',
            email='a@example.com',
            password='x',
        )
        user.role = self.role_admin
        user.save()
        request.user = user

        class V(AdminRequiredMixin):
            pass

        view = V()
        view.request = request
        self.assertTrue(view.test_func())

        user.role = self.role_standard
        user.save()
        request.user.refresh_from_db()
        self.assertFalse(view.test_func())

    def test_role_required_mixin_allows_configured_role(self):
        factory = RequestFactory()
        request = factory.get('/')
        user = User.objects.create_user(
            username='roleadm@example.com',
            email='roleadm@example.com',
            password='x',
        )
        user.role = self.role_admin
        user.save()
        request.user = user

        class V(RoleRequiredMixin):
            allowed_roles = (ROLE_NAME_ADMINISTRATOR,)

        view = V()
        view.request = request
        self.assertTrue(view.test_func())

    def test_role_required_mixin_blocks_other_role(self):
        factory = RequestFactory()
        request = factory.get('/')
        user = User.objects.create_user(
            username='rolestd@example.com',
            email='rolestd@example.com',
            password='x',
        )
        user.role = self.role_standard
        user.save()
        request.user = user

        class V(RoleRequiredMixin):
            allowed_roles = (ROLE_NAME_ADMINISTRATOR,)

        view = V()
        view.request = request
        self.assertFalse(view.test_func())

    def test_user_has_role_matches_constants(self):
        user = User.objects.create_user(
            username='roles@example.com',
            email='roles@example.com',
            password='x',
        )
        user.role = self.role_standard
        user.save()
        self.assertTrue(user_has_role(user, ROLE_NAME_STANDARD_USER))
        self.assertFalse(user_has_role(user, ROLE_NAME_ADMINISTRATOR))
