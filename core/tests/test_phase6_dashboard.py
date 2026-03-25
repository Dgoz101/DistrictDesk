"""Phase 6: dashboard aggregates and JSON API (admin-only)."""
import json
import sys
import unittest

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Role
from devices.models import Device, DeviceStatus, DeviceType
from tickets.models import Ticket, TicketCategory, PriorityLevel

User = get_user_model()

_SKIP_HTML_GET = sys.version_info >= (3, 14)
_SKIP_REASON = (
    'Django 4.2 test client + Python 3.14+: template context copy error; use Python 3.12-3.13 for GET HTML tests.'
)


class Phase6DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')
        cls.cat = TicketCategory.objects.create(name='Hardware', sort_order=0)
        cls.pri = PriorityLevel.objects.create(name='Medium', sort_order=1)
        cls.dtype = DeviceType.objects.create(name='Laptop')
        cls.dstatus = DeviceStatus.objects.create(name='In-service')

    def setUp(self):
        self.admin = User.objects.create_user(
            username='d6adm@example.com',
            email='d6adm@example.com',
            password='pass12345',
        )
        self.admin.role = self.role_admin
        self.admin.save()
        self.std = User.objects.create_user(
            username='d6std@example.com',
            email='d6std@example.com',
            password='pass12345',
        )
        self.std.role = self.role_std
        self.std.save()

    def test_api_summary_admin_returns_json(self):
        Ticket.objects.create(
            title='T1',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.std,
        )
        Device.objects.create(
            asset_tag='Z-1',
            device_type=self.dtype,
            status=self.dstatus,
        )
        self.client.login(username='d6adm@example.com', password='pass12345')
        r = self.client.get('/dashboard/api/summary/')
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content.decode())
        self.assertIn('summary', data)
        self.assertIn('chart_data', data)
        self.assertEqual(data['summary']['total_tickets'], 1)
        self.assertEqual(data['summary']['total_devices'], 1)
        self.assertIn('tickets_by_status', data['chart_data'])
        self.assertIn('tickets_trend', data['chart_data'])

    def test_api_summary_forbidden_for_standard_user(self):
        self.client.login(username='d6std@example.com', password='pass12345')
        r = self.client.get('/dashboard/api/summary/')
        self.assertEqual(r.status_code, 403)

    def test_api_summary_forbidden_anonymous(self):
        """AdminRequiredMixin uses raise_exception; unauthenticated users get 403 (not redirect)."""
        r = self.client.get('/dashboard/api/summary/')
        self.assertEqual(r.status_code, 403)

    @unittest.skipIf(_SKIP_HTML_GET, _SKIP_REASON)
    def test_dashboard_home_renders_for_admin(self):
        self.client.login(username='d6adm@example.com', password='pass12345')
        r = self.client.get('/dashboard/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Dashboard')
