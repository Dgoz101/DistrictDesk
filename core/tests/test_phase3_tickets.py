"""Phase 3: ticket create, list (scoped), detail, status history."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Role
from tickets.models import Ticket, TicketCategory, PriorityLevel, TicketStatusHistory

User = get_user_model()


class Phase3TicketTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = TicketCategory.objects.create(name='Hardware', sort_order=0)
        cls.pri = PriorityLevel.objects.create(name='Medium', sort_order=1)
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')

    def setUp(self):
        self.user_std = User.objects.create_user(
            username='u1@example.com',
            email='u1@example.com',
            password='pass12345',
        )
        self.user_std.role = self.role_std
        self.user_std.save()
        self.user_other = User.objects.create_user(
            username='u2@example.com',
            email='u2@example.com',
            password='pass12345',
        )
        self.user_other.role = self.role_std
        self.user_other.save()
        self.user_adm = User.objects.create_user(
            username='adm@example.com',
            email='adm@example.com',
            password='pass12345',
        )
        self.user_adm.role = self.role_admin
        self.user_adm.save()

    def test_create_ticket_and_status_history(self):
        self.client.login(username='u1@example.com', password='pass12345')
        response = self.client.post(
            '/tickets/new/',
            {
                'title': 'Printer issue',
                'description': 'Will not print.',
                'category': self.cat.pk,
                'priority': self.pri.pk,
            },
        )
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.get(title='Printer issue')
        self.assertEqual(ticket.submitter_id, self.user_std.id)
        self.assertEqual(ticket.status, Ticket.Status.OPEN)
        self.assertEqual(ticket.status_history.count(), 1)
        row = ticket.status_history.first()
        self.assertEqual(row.new_status, Ticket.Status.OPEN)
        self.assertEqual(row.changed_by_id, self.user_std.id)

    def test_list_shows_only_own_for_standard_user(self):
        Ticket.objects.create(
            title='Mine',
            description='x',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.user_std,
        )
        Ticket.objects.create(
            title='Theirs',
            description='y',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.user_other,
        )
        self.client.login(username='u1@example.com', password='pass12345')
        response = self.client.get('/tickets/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mine')
        self.assertNotContains(response, 'Theirs')

    def test_list_shows_all_for_admin(self):
        Ticket.objects.create(
            title='Mine',
            description='x',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.user_std,
        )
        Ticket.objects.create(
            title='Theirs',
            description='y',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.user_other,
        )
        self.client.login(username='adm@example.com', password='pass12345')
        response = self.client.get('/tickets/')
        self.assertContains(response, 'Mine')
        self.assertContains(response, 'Theirs')

    def test_detail_submitter_allowed(self):
        t = Ticket.objects.create(
            title='T',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.user_std,
        )
        TicketStatusHistory.objects.create(
            ticket=t,
            old_status='',
            new_status=Ticket.Status.OPEN,
            changed_by=self.user_std,
        )
        self.client.login(username='u1@example.com', password='pass12345')
        r = self.client.get(f'/tickets/{t.pk}/')
        self.assertEqual(r.status_code, 200)

    def test_detail_other_user_forbidden(self):
        t = Ticket.objects.create(
            title='Private',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.user_other,
        )
        self.client.login(username='u1@example.com', password='pass12345')
        r = self.client.get(f'/tickets/{t.pk}/')
        self.assertEqual(r.status_code, 403)

    def test_detail_admin_allowed(self):
        t = Ticket.objects.create(
            title='Other user ticket',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.user_other,
        )
        self.client.login(username='adm@example.com', password='pass12345')
        r = self.client.get(f'/tickets/{t.pk}/')
        self.assertEqual(r.status_code, 200)
