"""
Create default DeviceType and DeviceStatus records if they don't exist.
Run after migrations: python manage.py seed_device_lookups
"""
from django.core.management.base import BaseCommand

from devices.models import DeviceStatus, DeviceType


class Command(BaseCommand):
    help = 'Create default device types and statuses.'

    def handle(self, *args, **options):
        types = ['Laptop', 'Desktop', 'Printer', 'Tablet', 'Monitor', 'Other']
        for name in types:
            _, created = DeviceType.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created device type: {name}"))

        statuses = ['In-service', 'Checked-out', 'Repair', 'Retired']
        for name in statuses:
            _, created = DeviceStatus.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created device status: {name}"))

        self.stdout.write(self.style.SUCCESS('Device lookups ready.'))
