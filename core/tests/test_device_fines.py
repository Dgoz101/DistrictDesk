"""Device checkout fines: late fees, damage catalog, return inspection."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from accounts.models import Role
from devices.models import (
    Device,
    DeviceCheckout,
    DeviceCheckoutPolicy,
    DeviceFine,
    DeviceFineType,
    DeviceStatus,
    DeviceType,
)

User = get_user_model()


class DeviceFineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.dtype = DeviceType.objects.create(name='Chromebook')
        cls.dstatus = DeviceStatus.objects.create(name='In-service')
        cls.dstatus_co = DeviceStatus.objects.create(name='Checked-out')
        DeviceFineType.objects.create(
            code='screen_cracked',
            name='Broken screen',
            default_amount=Decimal('100.00'),
            sort_order=1,
        )
        DeviceFineType.objects.create(
            code='late_return',
            name='Late return',
            default_amount=Decimal('0.00'),
            sort_order=200,
            is_system=True,
        )
        policy = DeviceCheckoutPolicy.get_solo()
        policy.late_fee_enabled = True
        policy.late_fee_per_day = Decimal('5.00')
        policy.late_grace_days = 0
        policy.late_fee_max_amount = Decimal('50.00')
        policy.save()

    def setUp(self):
        self.admin = User.objects.create_user(
            username='fineadm@example.com',
            email='fineadm@example.com',
            password='pass12345',
        )
        self.admin.role = self.role_admin
        self.admin.save()
        self.borrower = User.objects.create_user(
            username='borrower@example.com',
            email='borrower@example.com',
            password='pass12345',
        )
        self.borrower.role = self.role_std
        self.borrower.save()
        self.device = Device.objects.create(
            asset_tag='CB-001',
            device_type=self.dtype,
            status=self.dstatus_co,
        )

    def _open_checkout(self, *, due_days_ago=2):
        due = timezone.now() - timedelta(days=due_days_ago)
        return DeviceCheckout.objects.create(
            device=self.device,
            checked_out_to=self.borrower,
            due_at=due,
            created_by=self.admin,
        )

    def test_return_inspection_no_damage(self):
        self._open_checkout(due_days_ago=0)
        self.client.login(username='fineadm@example.com', password='pass12345')
        r = self.client.post(
            f'/devices/{self.device.pk}/return/',
            {'condition': 'no_damage'},
        )
        self.assertRedirects(r, f'/devices/{self.device.pk}/', fetch_redirect_response=False)
        co = DeviceCheckout.objects.get(device=self.device)
        self.assertIsNotNone(co.returned_at)
        self.assertEqual(co.fines.count(), 0)

    def test_return_inspection_with_late_fee(self):
        self._open_checkout(due_days_ago=3)
        self.client.login(username='fineadm@example.com', password='pass12345')
        r = self.client.post(
            f'/devices/{self.device.pk}/return/',
            {
                'condition': 'no_damage',
                'apply_late_fee': '1',
                'late_fee_amount': '12.50',
            },
        )
        self.assertRedirects(r, f'/devices/{self.device.pk}/', fetch_redirect_response=False)
        fine = DeviceFine.objects.get(checkout__device=self.device, is_late_fee=True)
        self.assertEqual(fine.amount, Decimal('12.50'))
        self.assertEqual(fine.status, DeviceFine.Status.PENDING)

    def test_return_inspection_damage_fine_editable_amount(self):
        self._open_checkout(due_days_ago=0)
        ft = DeviceFineType.objects.get(code='screen_cracked')
        self.client.login(username='fineadm@example.com', password='pass12345')
        r = self.client.post(
            f'/devices/{self.device.pk}/return/',
            {
                'condition': 'assess',
                'assess_fines': '1',
                'fine_type': [str(ft.pk)],
                f'fine_qty_{ft.pk}': '1',
                f'fine_amount_{ft.pk}': '75.00',
            },
        )
        self.assertRedirects(r, f'/devices/{self.device.pk}/', fetch_redirect_response=False)
        fine = DeviceFine.objects.get(checkout__device=self.device, fine_type=ft)
        self.assertEqual(fine.amount, Decimal('75.00'))

    def test_admin_updates_checkout_policy(self):
        self.client.login(username='fineadm@example.com', password='pass12345')
        r = self.client.post(
            '/devices/settings/checkout-policy/',
            {
                'late_fee_enabled': 'on',
                'late_fee_per_day': '7.50',
                'late_grace_days': '2',
                'late_fee_max_amount': '100.00',
            },
        )
        self.assertRedirects(r, '/devices/settings/', fetch_redirect_response=False)
        policy = DeviceCheckoutPolicy.get_solo()
        self.assertEqual(policy.late_fee_per_day, Decimal('7.50'))
        self.assertEqual(policy.late_grace_days, 2)

    def test_fine_list_admin_only(self):
        self.client.login(username='borrower@example.com', password='pass12345')
        self.assertEqual(self.client.get('/devices/fines/').status_code, 403)

    def test_create_fine_type(self):
        self.client.login(username='fineadm@example.com', password='pass12345')
        r = self.client.post(
            '/devices/settings/fine-types/new/',
            {
                'name': 'Custom damage',
                'description': 'Test',
                'default_amount': '25.00',
                'sort_order': '50',
                'is_active': 'on',
            },
        )
        self.assertRedirects(r, '/devices/settings/fine-types/', fetch_redirect_response=False)
        self.assertTrue(DeviceFineType.objects.filter(name='Custom damage').exists())
