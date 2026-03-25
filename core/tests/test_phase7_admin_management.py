"""Phase 7: user management (FR-38) and ticket lookup settings (FR-39)."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Role
from tickets.models import Ticket, TicketCategory, PriorityLevel

User = get_user_model()


class Phase7AdminManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')
        cls.cat = TicketCategory.objects.create(name='Hardware', sort_order=0)
        cls.pri = PriorityLevel.objects.create(name='Medium', sort_order=1)

    def setUp(self):
        self.admin = User.objects.create_user(
            username='p7adm@example.com',
            email='p7adm@example.com',
            password='pass12345',
        )
        self.admin.role = self.role_admin
        self.admin.save()
        self.std = User.objects.create_user(
            username='p7std@example.com',
            email='p7std@example.com',
            password='pass12345',
        )
        self.std.role = self.role_std
        self.std.save()

    def test_admin_post_create_category(self):
        self.client.login(username='p7adm@example.com', password='pass12345')
        r = self.client.post(
            '/tickets/settings/categories/new/',
            {'name': 'New Cat', 'sort_order': 5},
        )
        self.assertRedirects(r, '/tickets/settings/categories/', fetch_redirect_response=False)
        self.assertTrue(TicketCategory.objects.filter(name='New Cat').exists())

    def test_admin_post_edit_user_role(self):
        self.client.login(username='p7adm@example.com', password='pass12345')
        r = self.client.post(
            f'/accounts/users/{self.std.pk}/edit/',
            {'role': self.role_admin.pk, 'is_active': 'on'},
        )
        self.assertRedirects(r, '/accounts/users/', fetch_redirect_response=False)
        self.std.refresh_from_db()
        self.assertEqual(self.std.role_id, self.role_admin.id)

    def test_standard_user_cannot_edit_users(self):
        self.client.login(username='p7std@example.com', password='pass12345')
        r = self.client.post(
            f'/accounts/users/{self.admin.pk}/edit/',
            {'role': self.role_std.pk, 'is_active': 'on'},
        )
        self.assertEqual(r.status_code, 403)

    def test_standard_user_cannot_manage_categories(self):
        self.client.login(username='p7std@example.com', password='pass12345')
        r = self.client.post(
            '/tickets/settings/categories/new/',
            {'name': 'X', 'sort_order': 0},
        )
        self.assertEqual(r.status_code, 403)

    def test_delete_category_without_tickets(self):
        c = TicketCategory.objects.create(name='Orphan', sort_order=99)
        self.client.login(username='p7adm@example.com', password='pass12345')
        r = self.client.post(f'/tickets/settings/categories/{c.pk}/delete/')
        self.assertRedirects(r, '/tickets/settings/categories/', fetch_redirect_response=False)
        self.assertFalse(TicketCategory.objects.filter(pk=c.pk).exists())

    def test_delete_category_with_ticket_blocked(self):
        t = Ticket.objects.create(
            title='Hold cat',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.std,
        )
        self.assertIsNotNone(t.pk)
        self.client.login(username='p7adm@example.com', password='pass12345')
        r = self.client.post(f'/tickets/settings/categories/{self.cat.pk}/delete/')
        self.assertRedirects(r, '/tickets/settings/categories/', fetch_redirect_response=False)
        self.assertTrue(TicketCategory.objects.filter(pk=self.cat.pk).exists())
