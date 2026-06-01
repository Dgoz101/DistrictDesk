"""
Create default Chromebook-oriented fine types and checkout policy.
Run after migrations: python manage.py seed_device_fine_types
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from devices.models import DeviceCheckoutPolicy, DeviceFineType, DeviceType


DEFAULT_FINE_TYPES = [
    ('screen_cracked', 'Broken / cracked screen', 'Display glass or LCD cracked/shattered.', '100.00', 10),
    ('screen_defect', 'Screen defect', 'Lines, dead pixels, or dim display without cracked glass.', '60.00', 20),
    ('keyboard_liquid', 'Keyboard liquid damage', 'Spill or sticky keys from liquid.', '75.00', 30),
    ('keyboard_not_working', 'Keyboard not working', 'Multiple keys or entire keyboard non-functional.', '80.00', 40),
    ('key_missing', 'Missing key(s)', 'Per keycap missing; quantity = number of keys.', '10.00', 50),
    ('trackpad_damage', 'Trackpad damage', 'Trackpad clicks, drag, or surface damage.', '45.00', 60),
    ('bezel_damage', 'Bezel / frame damage', 'Cracked or broken plastic bezel/frame.', '35.00', 70),
    ('hinge_damage', 'Hinge damage', 'Loose, cracked, or broken hinges.', '55.00', 80),
    ('case_damage', 'Case / shell damage', 'Dents, cracks, or holes in outer shell.', '40.00', 90),
    ('charger_missing', 'Missing charger', 'AC adapter not returned with device.', '30.00', 100),
    ('charger_damaged', 'Damaged charger', 'Frayed cable or broken adapter.', '20.00', 110),
    ('asset_tag_removed', 'Asset tag removed/defaced', 'District asset tag missing or unreadable.', '15.00', 120),
    ('late_return', 'Late return', 'Auto-calculated from checkout policy; amount editable at return.', '0.00', 200, True),
    ('other', 'Other damage', 'Describe in notes; enter amount at return.', '0.00', 999, False),
]


class Command(BaseCommand):
    help = 'Create default device fine types, checkout policy, and Chromebook device type.'

    def handle(self, *args, **options):
        DeviceType.objects.get_or_create(name='Chromebook')

        for row in DEFAULT_FINE_TYPES:
            code, name, desc, amount, order = row[:5]
            is_system = row[5] if len(row) > 5 else False
            _, created = DeviceFineType.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'description': desc,
                    'default_amount': Decimal(amount),
                    'sort_order': order,
                    'is_active': True,
                    'is_system': is_system,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created fine type: {name}'))

        policy = DeviceCheckoutPolicy.get_solo()
        if policy.late_fee_per_day == Decimal('5.00'):
            policy.late_fee_enabled = True
            policy.late_fee_per_day = Decimal('5.00')
            policy.late_grace_days = 0
            policy.late_fee_max_amount = Decimal('50.00')
            policy.save()
        self.stdout.write(self.style.SUCCESS('Device fine types and checkout policy ready.'))
