"""
Create default TicketCategory and PriorityLevel records if they don't exist.
Run after migrations: python manage.py seed_ticket_lookups
"""
from django.core.management.base import BaseCommand

from tickets.models import PriorityLevel, TicketCategory


class Command(BaseCommand):
    help = 'Create default ticket categories and priority levels.'

    def handle(self, *args, **options):
        categories = [
            {'name': 'Hardware', 'sort_order': 0},
            {'name': 'Software', 'sort_order': 1},
            {'name': 'Access', 'sort_order': 2},
            {'name': 'Other', 'sort_order': 3},
        ]
        for c in categories:
            _, created = TicketCategory.objects.get_or_create(name=c['name'], defaults=c)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created category: {c['name']}"))

        priorities = [
            {'name': 'Low', 'sort_order': 0},
            {'name': 'Medium', 'sort_order': 1},
            {'name': 'High', 'sort_order': 2},
            {'name': 'Critical', 'sort_order': 3},
        ]
        for p in priorities:
            _, created = PriorityLevel.objects.get_or_create(name=p['name'], defaults=p)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created priority: {p['name']}"))

        self.stdout.write(self.style.SUCCESS('Ticket lookups ready.'))
