"""Phase 4: admin ticket assign, update, comments, filters (POST-focused for Py3.14 client)."""
import sys
import unittest

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Role
from tickets.models import (
    Ticket,
    TicketAssignment,
    TicketCategory,
    TicketComment,
    PriorityLevel,
)

User = get_user_model()

_SKIP_HTML_GET = sys.version_info >= (3, 14)
_SKIP_REASON = (
    'Django 4.2 test client + Python 3.14+: template context copy error; use Python 3.12-3.13 for GET HTML tests.'
)


class Phase4AdminTicketTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat_hw = TicketCategory.objects.create(name='Hardware', sort_order=0)
        cls.cat_sw = TicketCategory.objects.create(name='Software', sort_order=1)
        cls.pri_low = PriorityLevel.objects.create(name='Low', sort_order=0)
        cls.pri_high = PriorityLevel.objects.create(name='High', sort_order=2)
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')

    def setUp(self):
        self.user_std = User.objects.create_user(
            username='p4u1@example.com',
            email='p4u1@example.com',
            password='pass12345',
        )
        self.user_std.role = self.role_std
        self.user_std.save()
        self.user_adm = User.objects.create_user(
            username='p4adm@example.com',
            email='p4adm@example.com',
            password='pass12345',
        )
        self.user_adm.role = self.role_admin
        self.user_adm.save()

    def test_admin_post_update_resolved_sets_closed_at(self):
        t = Ticket.objects.create(
            title='Need fix',
            description='desc',
            category=self.cat_hw,
            priority=self.pri_low,
            status=Ticket.Status.OPEN,
            submitter=self.user_std,
        )
        self.assertIsNone(t.closed_at)
        self.client.login(username='p4adm@example.com', password='pass12345')
        r = self.client.post(
            f'/tickets/{t.pk}/admin/update/',
            {
                'status': Ticket.Status.RESOLVED,
                'priority': self.pri_low.pk,
                'category': self.cat_hw.pk,
            },
        )
        self.assertEqual(r.status_code, 302)
        t.refresh_from_db()
        self.assertEqual(t.status, Ticket.Status.RESOLVED)
        self.assertIsNotNone(t.closed_at)

    def test_admin_assign_moves_open_to_assigned(self):
        t = Ticket.objects.create(
            title='Assign me',
            description='d',
            category=self.cat_hw,
            priority=self.pri_low,
            status=Ticket.Status.OPEN,
            submitter=self.user_std,
        )
        self.client.login(username='p4adm@example.com', password='pass12345')
        r = self.client.post(
            f'/tickets/{t.pk}/assign/',
            {'assigned_to': self.user_adm.pk},
        )
        self.assertEqual(r.status_code, 302)
        t.refresh_from_db()
        self.assertEqual(t.status, Ticket.Status.ASSIGNED)
        self.assertTrue(
            TicketAssignment.objects.filter(
                ticket=t, assigned_to=self.user_adm, is_current=True
            ).exists()
        )

    def test_admin_post_comment(self):
        t = Ticket.objects.create(
            title='C',
            description='d',
            category=self.cat_hw,
            priority=self.pri_low,
            status=Ticket.Status.IN_PROGRESS,
            submitter=self.user_std,
        )
        self.client.login(username='p4adm@example.com', password='pass12345')
        r = self.client.post(
            f'/tickets/{t.pk}/comment/',
            {'body': 'Fixed the cable.', 'is_internal': 'on'},
        )
        self.assertEqual(r.status_code, 302)
        c = TicketComment.objects.get(ticket=t)
        self.assertEqual(c.body, 'Fixed the cable.')
        self.assertTrue(c.is_internal)
        self.assertEqual(c.author_id, self.user_adm.id)

    def test_standard_user_admin_posts_forbidden(self):
        t = Ticket.objects.create(
            title='X',
            description='d',
            category=self.cat_hw,
            priority=self.pri_low,
            status=Ticket.Status.OPEN,
            submitter=self.user_std,
        )
        self.client.login(username='p4u1@example.com', password='pass12345')
        for url in (
            f'/tickets/{t.pk}/admin/update/',
            f'/tickets/{t.pk}/assign/',
            f'/tickets/{t.pk}/comment/',
        ):
            r = self.client.post(
                url,
                {
                    'status': Ticket.Status.CLOSED,
                    'priority': self.pri_low.pk,
                    'category': self.cat_hw.pk,
                }
                if 'admin' in url
                else (
                    {'assigned_to': self.user_adm.pk}
                    if 'assign' in url
                    else {'body': 'nope', 'is_internal': ''}
                ),
            )
            self.assertEqual(r.status_code, 403, msg=url)

    @unittest.skipIf(_SKIP_HTML_GET, _SKIP_REASON)
    def test_admin_list_filter_search_in_html(self):
        Ticket.objects.create(
            title='Alpha printer',
            description='paper jam',
            category=self.cat_hw,
            priority=self.pri_low,
            status=Ticket.Status.OPEN,
            submitter=self.user_std,
        )
        Ticket.objects.create(
            title='Beta',
            description='other',
            category=self.cat_sw,
            priority=self.pri_high,
            status=Ticket.Status.RESOLVED,
            submitter=self.user_std,
        )
        self.client.login(username='p4adm@example.com', password='pass12345')
        r = self.client.get('/tickets/', {'q': 'printer'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Alpha printer')
        self.assertNotContains(r, 'Beta')
