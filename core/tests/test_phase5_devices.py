"""Phase 5: device list/create/edit (admin-only); POST-focused tests."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import Role
from core.models import Location
from devices.models import Device, DeviceCheckout, DeviceStatus, DeviceType

User = get_user_model()


class Phase5DeviceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dtype = DeviceType.objects.create(name='Laptop')
        cls.dstatus = DeviceStatus.objects.create(name='In-service')
        cls.dstatus_co = DeviceStatus.objects.create(name='Checked-out')
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
                'purchase_date': '',
                'warranty_end_date': '',
                'purchase_vendor': '',
                'purchase_order': '',
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
                'purchase_date': '',
                'warranty_end_date': '',
                'purchase_vendor': '',
                'purchase_order': '',
            },
        )
        self.assertRedirects(r, '/devices/', fetch_redirect_response=False)
        d.refresh_from_db()
        self.assertEqual(d.model, 'Updated model')
        self.assertEqual(d.assigned_user_id, self.admin.id)
        self.assertEqual(d.location_id, self.loc.id)

    def test_admin_get_print_label(self):
        d = Device.objects.create(
            asset_tag='DT-PRINT',
            device_type=self.dtype,
            model='X1',
            serial_number='SN-P',
            status=self.dstatus,
            location=self.loc,
        )
        self.client.login(username='d5adm@example.com', password='pass12345')
        r = self.client.get(f'/devices/{d.pk}/print/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'DT-PRINT')
        self.assertContains(r, 'Laptop')
        self.assertContains(r, 'Room 101')
        self.assertContains(r, 'data:image/svg+xml')

    def test_standard_user_print_label_forbidden(self):
        d = Device.objects.create(
            asset_tag='DT-NO',
            device_type=self.dtype,
            status=self.dstatus,
        )
        self.client.login(username='d5std@example.com', password='pass12345')
        r = self.client.get(f'/devices/{d.pk}/print/')
        self.assertEqual(r.status_code, 403)

    def test_admin_post_print_selected_two_devices(self):
        d1 = Device.objects.create(
            asset_tag='DT-B1',
            device_type=self.dtype,
            status=self.dstatus,
        )
        d2 = Device.objects.create(
            asset_tag='DT-B2',
            device_type=self.dtype,
            model='Mini',
            status=self.dstatus,
        )
        self.client.login(username='d5adm@example.com', password='pass12345')
        r = self.client.post(
            '/devices/print-selected/',
            {'device_ids': [str(d2.pk), str(d1.pk)]},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'DT-B1')
        self.assertContains(r, 'DT-B2')
        self.assertContains(r, 'Mini')

    def test_admin_post_print_selected_empty_redirects(self):
        self.client.login(username='d5adm@example.com', password='pass12345')
        r = self.client.post('/devices/print-selected/', {}, follow=True)
        self.assertEqual(r.redirect_chain[0][0], '/devices/')
        self.assertContains(r, 'Select at least one')

    def test_standard_user_print_selected_forbidden(self):
        d = Device.objects.create(
            asset_tag='DT-BLK',
            device_type=self.dtype,
            status=self.dstatus,
        )
        self.client.login(username='d5std@example.com', password='pass12345')
        r = self.client.post(
            '/devices/print-selected/',
            {'device_ids': [str(d.pk)]},
        )
        self.assertEqual(r.status_code, 403)

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

    def test_public_device_report_anonymous_ok(self):
        d = Device.objects.create(
            asset_tag='DT-PUB',
            device_type=self.dtype,
            status=self.dstatus,
        )
        r = self.client.get(f'/devices/report/{d.public_report_uuid}/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'DT-PUB')
        self.assertContains(r, 'Open a support ticket')

    def test_admin_warranty_within_90_lists_matching_only(self):
        today = timezone.localdate()
        d_in = Device.objects.create(
            asset_tag='DT-WIN',
            device_type=self.dtype,
            status=self.dstatus,
            warranty_end_date=today + timedelta(days=10),
        )
        d_out = Device.objects.create(
            asset_tag='DT-WOUT',
            device_type=self.dtype,
            status=self.dstatus,
            warranty_end_date=today + timedelta(days=100),
        )
        self.client.login(username='d5adm@example.com', password='pass12345')
        r = self.client.get('/devices/?warranty_within=90')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, d_in.asset_tag)
        self.assertNotContains(r, d_out.asset_tag)

    def test_admin_checkout_then_return(self):
        d = Device.objects.create(
            asset_tag='DT-LOAN',
            device_type=self.dtype,
            status=self.dstatus,
        )
        self.client.login(username='d5adm@example.com', password='pass12345')
        r = self.client.post(
            f'/devices/{d.pk}/',
            {
                'action': 'checkout',
                'checked_out_to': str(self.std.pk),
                'due_at': '',
                'notes': 'class set',
            },
        )
        self.assertRedirects(r, f'/devices/{d.pk}/', fetch_redirect_response=False)
        d.refresh_from_db()
        self.assertEqual(d.status_id, self.dstatus_co.id)
        self.assertTrue(
            DeviceCheckout.objects.filter(device=d, returned_at__isnull=True).exists()
        )
        r2 = self.client.post(
            f'/devices/{d.pk}/return/',
            {'condition': 'no_damage'},
        )
        self.assertRedirects(r2, f'/devices/{d.pk}/', fetch_redirect_response=False)
        d.refresh_from_db()
        self.assertEqual(d.status_id, self.dstatus.id)
        self.assertFalse(
            DeviceCheckout.objects.filter(device=d, returned_at__isnull=True).exists()
        )

    def test_admin_export_csv_contains_asset_tag(self):
        Device.objects.create(
            asset_tag='DT-CSV',
            device_type=self.dtype,
            status=self.dstatus,
        )
        self.client.login(username='d5adm@example.com', password='pass12345')
        r = self.client.get('/devices/export.csv')
        self.assertEqual(r.status_code, 200)
        body = b''.join(r.streaming_content).decode()
        self.assertIn('asset_tag', body)
        self.assertIn('DT-CSV', body)

    def test_admin_csv_import_dry_run_counts(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        csv_text = (
            'asset_tag,device_type,status,model,serial_number,location,assigned_user,'
            'purchase_date,warranty_end_date,purchase_vendor,purchase_order,public_report_uuid\n'
            'DT-IMP99,Laptop,In-service,Test,,,,,,,\n'
        )
        self.client.login(username='d5adm@example.com', password='pass12345')
        f = SimpleUploadedFile('devices.csv', csv_text.encode('utf-8'), content_type='text/csv')
        r = self.client.post('/devices/import/', {'dry_run': '1', 'file': f}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Dry run')
        self.assertFalse(Device.objects.filter(asset_tag='DT-IMP99').exists())

    def test_ticket_create_prefills_device_query_param(self):
        d = Device.objects.create(
            asset_tag='DT-TIX',
            device_type=self.dtype,
            status=self.dstatus,
        )
        self.client.login(username='d5std@example.com', password='pass12345')
        r = self.client.get(f'/tickets/new/?device={d.pk}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['form'].initial.get('device'), d.pk)
