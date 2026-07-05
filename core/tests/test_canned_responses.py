"""Canned response snippets for admin ticket comments."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Role
from core.models import AdminAuditEntry
from tickets.models import CannedResponse, Ticket, TicketCategory, PriorityLevel

User = get_user_model()


class CannedResponseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')
        cls.cat = TicketCategory.objects.create(name='Hardware', sort_order=0)
        cls.pri = PriorityLevel.objects.create(name='Medium', sort_order=1)

    def setUp(self):
        self.admin = User.objects.create_user(
            username='can_adm@example.com',
            email='can_adm@example.com',
            password='pass12345',
        )
        self.admin.role = self.role_admin
        self.admin.save()
        self.std = User.objects.create_user(
            username='can_std@example.com',
            email='can_std@example.com',
            password='pass12345',
        )
        self.std.role = self.role_std
        self.std.save()

    def test_admin_create_canned_response(self):
        self.client.login(username='can_adm@example.com', password='pass12345')
        r = self.client.post(
            '/tickets/settings/canned/new/',
            {
                'title': 'Waiting on user',
                'body': 'Please reboot and let us know if the issue persists.',
                'sort_order': 0,
                'is_active': 'on',
            },
        )
        self.assertRedirects(r, '/tickets/settings/canned/', fetch_redirect_response=False)
        self.assertTrue(CannedResponse.objects.filter(title='Waiting on user').exists())
        self.assertTrue(
            AdminAuditEntry.objects.filter(
                entity_type=AdminAuditEntry.EntityType.CANNED_RESPONSE,
                action=AdminAuditEntry.Action.CREATE,
            ).exists()
        )

    def test_inactive_snippet_hidden_on_ticket_detail(self):
        CannedResponse.objects.create(
            title='Active one',
            body='Hello',
            is_active=True,
        )
        CannedResponse.objects.create(
            title='Hidden one',
            body='Secret template',
            is_active=False,
        )
        ticket = Ticket.objects.create(
            title='Test',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.std,
        )
        self.client.login(username='can_adm@example.com', password='pass12345')
        r = self.client.get(f'/tickets/{ticket.pk}/')
        self.assertContains(r, 'Active one')
        self.assertNotContains(r, 'Hidden one')
        self.assertContains(r, 'canned-responses-data')
        self.assertContains(r, 'ticket-comment-body')

    def test_post_comment_with_snippet_body(self):
        CannedResponse.objects.create(
            title='Thanks',
            body='We are on it.',
            is_active=True,
        )
        ticket = Ticket.objects.create(
            title='Test',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.std,
        )
        self.client.login(username='can_adm@example.com', password='pass12345')
        r = self.client.post(
            f'/tickets/{ticket.pk}/comment/',
            {'body': 'We are on it.', 'is_internal': ''},
        )
        self.assertRedirects(r, f'/tickets/{ticket.pk}/', fetch_redirect_response=False)
        self.assertEqual(ticket.comments.get().body, 'We are on it.')

    def test_standard_user_cannot_manage_canned_responses(self):
        self.client.login(username='can_std@example.com', password='pass12345')
        self.assertEqual(self.client.get('/tickets/settings/canned/').status_code, 403)

    def test_delete_canned_response(self):
        snippet = CannedResponse.objects.create(title='Remove me', body='x')
        self.client.login(username='can_adm@example.com', password='pass12345')
        r = self.client.post(f'/tickets/settings/canned/{snippet.pk}/delete/')
        self.assertRedirects(r, '/tickets/settings/canned/', fetch_redirect_response=False)
        self.assertFalse(CannedResponse.objects.filter(pk=snippet.pk).exists())

    def test_settings_hub_links_canned_responses(self):
        self.client.login(username='can_adm@example.com', password='pass12345')
        r = self.client.get('/tickets/settings/')
        self.assertContains(r, 'Canned responses')
        self.assertContains(r, '/tickets/settings/canned/')
