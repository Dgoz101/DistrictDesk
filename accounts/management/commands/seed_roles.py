"""
Create default Role records (Standard User, Administrator) if they don't exist.
Run after migrations: python manage.py seed_roles
"""
from django.core.management.base import BaseCommand

from accounts.models import Role


class Command(BaseCommand):
    help = 'Create default Role records for DistrictDesk RBAC.'

    def handle(self, *args, **options):
        defaults = [
            {'name': 'Standard User'},
            {'name': 'Administrator'},
        ]
        created = 0
        for d in defaults:
            _, was_created = Role.objects.get_or_create(name=d['name'], defaults=d)
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created role: {d['name']}"))
        if not created:
            self.stdout.write('All roles already exist.')
