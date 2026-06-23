"""Admin ticket CSV export (filtered list)."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import Role
from tickets.models import Ticket, TicketCategory, PriorityLevel

User = get_user_model()


class TicketCsvExportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = TicketCategory.objects.create(name='Hardware', sort_order=0)
        cls.pri = PriorityLevel.objects.create(name='Medium', sort_order=1)
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')

    def setUp(self):
        self.std = User.objects.create_user(
            username='csv_std@example.com',
            email='csv_std@example.com',
            password='pass12345',
        )
        self.std.role = self.role_std
        self.std.save()
        self.admin = User.objects.create_user(
            username='csv_adm@example.com',
            email='csv_adm@example.com',
            password='pass12345',
        )
        self.admin.role = self.role_admin
        self.admin.save()

    def _csv_body(self, response):
        return b''.join(response.streaming_content).decode('utf-8')

    def test_admin_export_csv_contains_ticket(self):
        Ticket.objects.create(
            title='Export me',
            description='Details here',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.std,
        )
        self.client.login(username='csv_adm@example.com', password='pass12345')
        r = self.client.get('/tickets/export.csv')
        self.assertEqual(r.status_code, 200)
        body = self._csv_body(r)
        self.assertIn('title', body)
        self.assertIn('Export me', body)
        self.assertIn('Details here', body)

    def test_admin_export_respects_status_filter(self):
        Ticket.objects.create(
            title='Open ticket',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.std,
        )
        Ticket.objects.create(
            title='Closed ticket',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.CLOSED,
            submitter=self.std,
        )
        self.client.login(username='csv_adm@example.com', password='pass12345')
        r = self.client.get(f'/tickets/export.csv?status={Ticket.Status.OPEN}')
        body = self._csv_body(r)
        self.assertIn('Open ticket', body)
        self.assertNotIn('Closed ticket', body)

    def test_admin_export_overdue_filter(self):
        overdue = Ticket.objects.create(
            title='Late item',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.std,
        )
        overdue.due_at = timezone.now() - timedelta(days=1)
        overdue.save(update_fields=['due_at'])
        Ticket.objects.create(
            title='On time',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.std,
            due_at=timezone.now() + timedelta(days=5),
        )
        self.client.login(username='csv_adm@example.com', password='pass12345')
        r = self.client.get('/tickets/export.csv?overdue=1')
        body = self._csv_body(r)
        self.assertIn('Late item', body)
        self.assertNotIn('On time', body)

    def test_standard_user_forbidden(self):
        self.client.login(username='csv_std@example.com', password='pass12345')
        self.assertEqual(self.client.get('/tickets/export.csv').status_code, 403)

    def test_anonymous_redirects_to_login(self):
        r = self.client.get('/tickets/export.csv')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/accounts/login/', r['Location'])

    def test_admin_list_shows_export_link(self):
        self.client.login(username='csv_adm@example.com', password='pass12345')
        r = self.client.get('/tickets/')
        self.assertContains(r, 'Export CSV')
        self.assertContains(r, '/tickets/export.csv')
