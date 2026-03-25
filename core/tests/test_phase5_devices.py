"""Phase 5: device list/create/edit (admin-only); POST-focused tests."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Role
from core.models import Location
from devices.models import Device, DeviceStatus, DeviceType

User = get_user_model()


class Phase5DeviceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dtype = DeviceType.objects.create(name='Laptop')
        cls.dstatus = DeviceStatus.objects.create(name='In-service')
        cls.loc = Location.objects.create(name='Room 101')
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')

    def setUp(self):
        self.admin = User.objects.create_user(
            username='d5adm@example.com',
            email='d5adm@example.com',
            password='pass12345',
        )
        self.admin.role = self.role_admin
        self.admin.save()
        self.std = User.objects.create_user(
            username='d5std@example.com',
            email='d5std@example.com',
            password='pass12345',
        )
        self.std.role = self.role_std
        self.std.save()

    def test_admin_post_create_device(self):
        self.client.login(username='d5adm@example.com', password='pass12345')
        r = self.client.post(
            '/devices/new/',
            {
                'asset_tag': 'DT-1001',
                'device_type': self.dtype.pk,
                'model': 'ThinkPad',
                'serial_number': 'SN1',
                'status': self.dstatus.pk,
                'assigned_user': '',
                'location': '',
            },
        )
        self.assertRedirects(r, '/devices/', fetch_redirect_response=False)
        d = Device.objects.get(asset_tag='DT-1001')
        self.assertEqual(d.model, 'ThinkPad')
        self.assertIsNone(d.assigned_user_id)

    def test_admin_post_update_device(self):
        d = Device.objects.create(
            asset_tag='DT-2002',
            device_type=self.dtype,
            model='Old',
            status=self.dstatus,
        )
        self.client.login(username='d5adm@example.com', password='pass12345')
        r = self.client.post(
            f'/devices/{d.pk}/edit/',
            {
                'asset_tag': 'DT-2002',
                'device_type': self.dtype.pk,
                'model': 'Updated model',
                'serial_number': '',
                'status': self.dstatus.pk,
                'assigned_user': self.admin.pk,
                'location': self.loc.pk,
            },
        )
        self.assertRedirects(r, '/devices/', fetch_redirect_response=False)
        d.refresh_from_db()
        self.assertEqual(d.model, 'Updated model')
        self.assertEqual(d.assigned_user_id, self.admin.id)
        self.assertEqual(d.location_id, self.loc.id)

    def test_standard_user_post_create_forbidden(self):
        self.client.login(username='d5std@example.com', password='pass12345')
        r = self.client.post(
            '/devices/new/',
            {
                'asset_tag': 'X-1',
                'device_type': self.dtype.pk,
                'model': '',
                'serial_number': '',
                'status': self.dstatus.pk,
            },
        )
        self.assertEqual(r.status_code, 403)
        self.assertFalse(Device.objects.filter(asset_tag='X-1').exists())
