"""Ticket SLA: due dates from priority, manual override, overdue on admin list."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import Role
from tickets.models import PriorityLevel, Ticket, TicketCategory
from tickets.services import apply_admin_ticket_update
from tickets.sla_service import apply_ticket_due_on_create, due_at_from_priority, ticket_is_overdue

User = get_user_model()


class TicketSlaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')
        cls.cat = TicketCategory.objects.create(name='Hardware', sort_order=0)
        cls.pri_low = PriorityLevel.objects.create(name='Low', sort_order=0, due_days=14)
        cls.pri_high = PriorityLevel.objects.create(name='High', sort_order=1, due_days=3)

    def setUp(self):
        self.std = User.objects.create_user(
            username='sla_std@example.com',
            email='sla_std@example.com',
            password='pass12345',
        )
        self.std.role = self.role_std
        self.std.save()
        self.admin = User.objects.create_user(
            username='sla_adm@example.com',
            email='sla_adm@example.com',
            password='pass12345',
        )
        self.admin.role = self.role_admin
        self.admin.save()

    def _create_ticket(self, **kwargs):
        defaults = {
            'title': 'SLA ticket',
            'description': 'Test',
            'category': self.cat,
            'priority': self.pri_low,
            'status': Ticket.Status.OPEN,
            'submitter': self.std,
        }
        defaults.update(kwargs)
        ticket = Ticket.objects.create(**defaults)
        apply_ticket_due_on_create(ticket)
        ticket.refresh_from_db()
        return ticket

    def test_create_sets_due_from_priority(self):
        ticket = self._create_ticket()
        expected = due_at_from_priority(ticket.created_at, self.pri_low)
        self.assertEqual(ticket.due_at, expected)
        self.assertFalse(ticket.due_at_is_manual)

    def test_admin_manual_due_override(self):
        ticket = self._create_ticket()
        manual = timezone.now() + timedelta(days=2)
        apply_admin_ticket_update(
            ticket,
            self.admin,
            category=self.cat,
            priority=self.pri_low,
            new_status=Ticket.Status.OPEN,
            old_status=Ticket.Status.OPEN,
            due_at=manual,
            old_due_at=ticket.due_at,
            due_at_changed=True,
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.due_at.replace(microsecond=0), manual.replace(microsecond=0))
        self.assertTrue(ticket.due_at_is_manual)

    def test_priority_change_recalculates_when_not_manual(self):
        ticket = self._create_ticket()
        old_due = ticket.due_at
        apply_admin_ticket_update(
            ticket,
            self.admin,
            category=self.cat,
            priority=self.pri_high,
            new_status=Ticket.Status.OPEN,
            old_status=Ticket.Status.OPEN,
            old_priority=self.pri_low,
        )
        ticket.refresh_from_db()
        expected = due_at_from_priority(ticket.created_at, self.pri_high)
        self.assertEqual(ticket.due_at, expected)
        self.assertNotEqual(ticket.due_at, old_due)

    def test_priority_change_keeps_manual_due(self):
        ticket = self._create_ticket()
        manual = timezone.now() + timedelta(days=30)
        ticket.due_at = manual
        ticket.due_at_is_manual = True
        ticket.save(update_fields=['due_at', 'due_at_is_manual'])
        apply_admin_ticket_update(
            ticket,
            self.admin,
            category=self.cat,
            priority=self.pri_high,
            new_status=Ticket.Status.OPEN,
            old_status=Ticket.Status.OPEN,
            old_priority=self.pri_low,
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.due_at.replace(microsecond=0), manual.replace(microsecond=0))

    def test_is_overdue_open_past_due(self):
        ticket = self._create_ticket()
        ticket.due_at = timezone.now() - timedelta(hours=1)
        ticket.save(update_fields=['due_at'])
        self.assertTrue(ticket_is_overdue(ticket))

    def test_not_overdue_when_resolved(self):
        ticket = self._create_ticket()
        ticket.due_at = timezone.now() - timedelta(hours=1)
        ticket.status = Ticket.Status.RESOLVED
        ticket.save(update_fields=['due_at', 'status'])
        self.assertFalse(ticket_is_overdue(ticket))

    def test_admin_list_shows_overdue_badge(self):
        ticket = self._create_ticket(title='Late printer')
        ticket.due_at = timezone.now() - timedelta(days=1)
        ticket.save(update_fields=['due_at'])
        self.client.login(username='sla_adm@example.com', password='pass12345')
        r = self.client.get('/tickets/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Overdue')
        self.assertContains(r, 'Late printer')

    def test_admin_overdue_filter(self):
        overdue = self._create_ticket(title='Overdue one')
        overdue.due_at = timezone.now() - timedelta(days=1)
        overdue.save(update_fields=['due_at'])
        ok = self._create_ticket(title='On track')
        ok.due_at = timezone.now() + timedelta(days=5)
        ok.save(update_fields=['due_at'])
        self.client.login(username='sla_adm@example.com', password='pass12345')
        r = self.client.get('/tickets/?overdue=1')
        self.assertContains(r, 'Overdue one')
        self.assertNotContains(r, 'On track')
