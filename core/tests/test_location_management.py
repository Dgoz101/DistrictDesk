"""Admin location CRUD (buildings/rooms for tickets and devices)."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Role
from core.models import AdminAuditEntry, Location
from devices.models import Device, DeviceStatus, DeviceType
from tickets.models import Ticket, TicketCategory, PriorityLevel

User = get_user_model()


class LocationManagementTests(TestCase):
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
            username='loc_adm@example.com',
            email='loc_adm@example.com',
            password='pass12345',
        )
        self.admin.role = self.role_admin
        self.admin.save()
        self.std = User.objects.create_user(
            username='loc_std@example.com',
            email='loc_std@example.com',
            password='pass12345',
        )
        self.std.role = self.role_std
        self.std.save()

    def test_admin_create_location(self):
        self.client.login(username='loc_adm@example.com', password='pass12345')
        r = self.client.post(
            '/locations/new/',
            {'name': 'Science Wing — 210', 'description': 'Chem lab prep room'},
        )
        self.assertRedirects(r, '/locations/', fetch_redirect_response=False)
        loc = Location.objects.get(name='Science Wing — 210')
        self.assertEqual(loc.description, 'Chem lab prep room')
        self.assertTrue(
            AdminAuditEntry.objects.filter(
                entity_type=AdminAuditEntry.EntityType.LOCATION,
                action=AdminAuditEntry.Action.CREATE,
                new_value='Science Wing — 210',
            ).exists()
        )

    def test_admin_edit_location_logs_audit(self):
        loc = Location.objects.create(name='Old name', description='')
        self.client.login(username='loc_adm@example.com', password='pass12345')
        r = self.client.post(
            f'/locations/{loc.pk}/edit/',
            {'name': 'New name', 'description': 'Updated'},
        )
        self.assertRedirects(r, '/locations/', fetch_redirect_response=False)
        loc.refresh_from_db()
        self.assertEqual(loc.name, 'New name')
        self.assertTrue(
            AdminAuditEntry.objects.filter(
                entity_type=AdminAuditEntry.EntityType.LOCATION,
                field_name='name',
                old_value='Old name',
                new_value='New name',
            ).exists()
        )

    def test_delete_unused_location(self):
        loc = Location.objects.create(name='Unused room')
        self.client.login(username='loc_adm@example.com', password='pass12345')
        r = self.client.post(f'/locations/{loc.pk}/delete/')
        self.assertRedirects(r, '/locations/', fetch_redirect_response=False)
        self.assertFalse(Location.objects.filter(pk=loc.pk).exists())

    def test_delete_location_with_ticket_blocked(self):
        loc = Location.objects.create(name='Ticket room')
        Ticket.objects.create(
            title='Broken projector',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.std,
            location=loc,
        )
        self.client.login(username='loc_adm@example.com', password='pass12345')
        r = self.client.post(f'/locations/{loc.pk}/delete/')
        self.assertRedirects(r, '/locations/', fetch_redirect_response=False)
        self.assertTrue(Location.objects.filter(pk=loc.pk).exists())

    def test_delete_location_with_device_blocked(self):
        loc = Location.objects.create(name='Device room')
        Device.objects.create(
            asset_tag='LOC-DEV-1',
            device_type=self.dtype,
            status=self.dstatus,
            location=loc,
        )
        self.client.login(username='loc_adm@example.com', password='pass12345')
        r = self.client.post(f'/locations/{loc.pk}/delete/')
        self.assertRedirects(r, '/locations/', fetch_redirect_response=False)
        self.assertTrue(Location.objects.filter(pk=loc.pk).exists())

    def test_standard_user_forbidden(self):
        self.client.login(username='loc_std@example.com', password='pass12345')
        self.assertEqual(self.client.get('/locations/').status_code, 403)
        self.assertEqual(
            self.client.post('/locations/new/', {'name': 'X', 'description': ''}).status_code,
            403,
        )

    def test_anonymous_redirects_to_login(self):
        r = self.client.get('/locations/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/accounts/login/', r['Location'])

    def test_nav_shows_locations_for_admin(self):
        self.client.login(username='loc_adm@example.com', password='pass12345')
        r = self.client.get('/tickets/')
        self.assertContains(r, 'href="/locations/"')
