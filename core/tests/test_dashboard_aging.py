"""Dashboard aging tickets KPI/chart and ticket list aging filters."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import Role
from tickets.models import Ticket, TicketCategory, PriorityLevel

User = get_user_model()


class DashboardAgingTicketsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')
        cls.cat = TicketCategory.objects.create(name='Hardware', sort_order=0)
        cls.pri = PriorityLevel.objects.create(name='Medium', sort_order=1)

    def setUp(self):
        self.std = User.objects.create_user(
            username='age_std@example.com',
            email='age_std@example.com',
            password='pass12345',
        )
        self.std.role = self.role_std
        self.std.save()
        self.admin = User.objects.create_user(
            username='age_adm@example.com',
            email='age_adm@example.com',
            password='pass12345',
        )
        self.admin.role = self.role_admin
        self.admin.save()

    def _ticket(self, title, *, days_ago=0, status=Ticket.Status.OPEN):
        t = Ticket.objects.create(
            title=title,
            description='d',
            category=self.cat,
            priority=self.pri,
            status=status,
            submitter=self.std,
        )
        if days_ago:
            Ticket.objects.filter(pk=t.pk).update(
                created_at=timezone.now() - timedelta(days=days_ago)
            )
            t.refresh_from_db()
        return t

    @override_settings(DASHBOARD_TICKET_AGING_DAYS=7)
    def test_dashboard_kpi_counts_aging_open_tickets(self):
        self._ticket('Fresh', days_ago=2)
        self._ticket('Old open', days_ago=10)
        self._ticket('Old closed', days_ago=10, status=Ticket.Status.CLOSED)
        self.client.login(username='age_adm@example.com', password='pass12345')
        r = self.client.get('/dashboard/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Open ≥ 7 days')
        self.assertContains(r, 'Old open')
        self.assertNotContains(r, 'Old closed')

    @override_settings(DASHBOARD_TICKET_AGING_DAYS=7)
    def test_dashboard_links_to_filtered_ticket_list(self):
        self._ticket('Stale ticket', days_ago=12)
        self.client.login(username='age_adm@example.com', password='pass12345')
        r = self.client.get('/dashboard/')
        self.assertContains(r, '/tickets/?aging_days=7')
        self.assertContains(r, 'sort=created_at')

    @override_settings(DASHBOARD_TICKET_AGING_DAYS=7)
    def test_ticket_list_aging_days_filter(self):
        self._ticket('Recent', days_ago=3)
        self._ticket('Aging', days_ago=8)
        self.client.login(username='age_adm@example.com', password='pass12345')
        r = self.client.get('/tickets/?aging_days=7')
        self.assertContains(r, 'Aging')
        self.assertNotContains(r, 'Recent')
        self.assertContains(r, 'Open tickets ≥ 7 days old')

    def test_ticket_list_aging_bucket_filter(self):
        self._ticket('Under week', days_ago=3)
        self._ticket('Two weeks', days_ago=10)
        self._ticket('Ancient', days_ago=40)
        self.client.login(username='age_adm@example.com', password='pass12345')
        r = self.client.get('/tickets/?aging_bucket=7-13')
        self.assertContains(r, 'Two weeks')
        self.assertNotContains(r, 'Under week')
        self.assertNotContains(r, 'Ancient')
        self.assertContains(r, 'Open tickets aged 7–13 days')

    @override_settings(DASHBOARD_TICKET_AGING_DAYS=7)
    def test_api_summary_includes_aging_data(self):
        self._ticket('Old', days_ago=10)
        self.client.login(username='age_adm@example.com', password='pass12345')
        r = self.client.get('/dashboard/api/summary/')
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data['summary']['aging_open_count'], 1)
        self.assertEqual(data['summary']['aging_threshold_days'], 7)
        self.assertIn('tickets_aging', data['chart_data'])
        self.assertIn('aging_open_preview', data)
