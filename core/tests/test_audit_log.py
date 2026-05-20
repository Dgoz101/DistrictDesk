"""Administrator audit log: roles, lookups, ticket category/priority."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Role
from core.models import AdminAuditEntry
from tickets.models import PriorityLevel, Ticket, TicketCategory
from tickets.services import apply_admin_ticket_update

User = get_user_model()


class AuditLogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')
        cls.cat_a = TicketCategory.objects.create(name='Hardware', sort_order=0)
        cls.cat_b = TicketCategory.objects.create(name='Software', sort_order=1)
        cls.pri_a = PriorityLevel.objects.create(name='Low', sort_order=0)
        cls.pri_b = PriorityLevel.objects.create(name='High', sort_order=1)

    def setUp(self):
        self.admin = User.objects.create_user(
            username='audit_adm@example.com',
            email='audit_adm@example.com',
            password='pass12345',
        )
        self.admin.role = self.role_admin
        self.admin.save()
        self.std = User.objects.create_user(
            username='audit_std@example.com',
            email='audit_std@example.com',
            password='pass12345',
        )
        self.std.role = self.role_std
        self.std.save()

    def test_user_role_change_creates_audit_rows(self):
        self.client.login(username='audit_adm@example.com', password='pass12345')
        r = self.client.post(
            f'/accounts/users/{self.std.pk}/edit/',
            {'role': self.role_admin.pk, 'is_active': 'on'},
        )
        self.assertRedirects(r, '/accounts/users/', fetch_redirect_response=False)
        rows = AdminAuditEntry.objects.filter(
            entity_type=AdminAuditEntry.EntityType.USER,
            object_id=self.std.pk,
        )
        self.assertTrue(rows.filter(field_name='role', new_value='Administrator').exists())

    def test_category_create_logs_audit(self):
        self.client.login(username='audit_adm@example.com', password='pass12345')
        self.client.post(
            '/tickets/settings/categories/new/',
            {'name': 'Network', 'sort_order': 3},
        )
        self.assertTrue(
            AdminAuditEntry.objects.filter(
                entity_type=AdminAuditEntry.EntityType.TICKET_CATEGORY,
                action=AdminAuditEntry.Action.CREATE,
                new_value='Network',
            ).exists()
        )

    def test_ticket_category_priority_update_logs_on_ticket(self):
        ticket = Ticket.objects.create(
            title='Audit ticket',
            description='d',
            category=self.cat_a,
            priority=self.pri_a,
            status=Ticket.Status.OPEN,
            submitter=self.std,
        )
        apply_admin_ticket_update(
            ticket,
            self.admin,
            category=self.cat_b,
            priority=self.pri_b,
            new_status=Ticket.Status.OPEN,
            old_status=Ticket.Status.OPEN,
            old_category=self.cat_a,
            old_priority=self.pri_a,
        )
        qs = AdminAuditEntry.objects.filter(ticket=ticket)
        self.assertTrue(qs.filter(field_name='category', old_value='Hardware', new_value='Software').exists())
        self.assertTrue(qs.filter(field_name='priority', old_value='Low', new_value='High').exists())
        self.assertFalse(
            AdminAuditEntry.objects.filter(ticket=ticket, field_name='status').exists()
        )

    def test_admin_audit_list_requires_admin(self):
        self.client.login(username='audit_std@example.com', password='pass12345')
        r = self.client.get('/accounts/audit/')
        self.assertEqual(r.status_code, 403)

    def test_admin_audit_list_200(self):
        self.client.login(username='audit_adm@example.com', password='pass12345')
        r = self.client.get('/accounts/audit/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Audit log')

    def test_successful_login_creates_audit_entry(self):
        before = AdminAuditEntry.objects.filter(
            entity_type=AdminAuditEntry.EntityType.AUTH,
            action=AdminAuditEntry.Action.LOGIN,
        ).count()
        r = self.client.post(
            '/accounts/login/',
            {'username': 'audit_adm@example.com', 'password': 'pass12345'},
        )
        self.assertEqual(r.status_code, 302)
        after = AdminAuditEntry.objects.filter(
            entity_type=AdminAuditEntry.EntityType.AUTH,
            action=AdminAuditEntry.Action.LOGIN,
            actor=self.admin,
        )
        self.assertEqual(after.count(), before + 1)
        self.assertIn('success', after.order_by('-created_at').first().new_value)

    def test_failed_login_creates_audit_entry_without_actor(self):
        r = self.client.post(
            '/accounts/login/',
            {'username': 'audit_adm@example.com', 'password': 'wrong-password'},
        )
        self.assertEqual(r.status_code, 200)
        entry = AdminAuditEntry.objects.filter(
            entity_type=AdminAuditEntry.EntityType.AUTH,
            action=AdminAuditEntry.Action.LOGIN,
            actor__isnull=True,
            object_label='audit_adm@example.com',
        ).order_by('-created_at').first()
        self.assertIsNotNone(entry)
        self.assertIn('failure', entry.new_value)

    def test_logout_creates_audit_entry(self):
        self.client.login(username='audit_adm@example.com', password='pass12345')
        before = AdminAuditEntry.objects.filter(action=AdminAuditEntry.Action.LOGOUT).count()
        self.client.post('/accounts/logout/')
        self.assertEqual(
            AdminAuditEntry.objects.filter(
                action=AdminAuditEntry.Action.LOGOUT,
                actor=self.admin,
            ).count(),
            before + 1,
        )

    def test_ticket_detail_includes_activity_section(self):
        ticket = Ticket.objects.create(
            title='Activity',
            description='d',
            category=self.cat_a,
            priority=self.pri_a,
            status=Ticket.Status.OPEN,
            submitter=self.std,
        )
        self.client.login(username='audit_std@example.com', password='pass12345')
        r = self.client.get(f'/tickets/{ticket.pk}/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Activity')
