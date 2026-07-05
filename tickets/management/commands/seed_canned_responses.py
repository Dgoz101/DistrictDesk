"""
Create default canned responses for ticket comments if they don't exist.
Run after migrations: python manage.py seed_canned_responses
"""
from django.core.management.base import BaseCommand

from tickets.models import CannedResponse


class Command(BaseCommand):
    help = 'Create default canned comment snippets for administrators.'

    def handle(self, *args, **options):
        snippets = [
            {
                'title': 'Received — investigating',
                'body': (
                    'Thank you for reporting this. We have received your ticket and are '
                    'looking into the issue. We will update you when we have more information.'
                ),
                'sort_order': 0,
            },
            {
                'title': 'Need more information',
                'body': (
                    'Could you provide any additional details that might help us troubleshoot? '
                    'For example: when the issue started, error messages, and whether it affects '
                    'one device or multiple users.'
                ),
                'sort_order': 1,
            },
            {
                'title': 'Resolved — please confirm',
                'body': (
                    'We believe this issue has been resolved. Please try again and reply here '
                    'if you still need assistance.'
                ),
                'sort_order': 2,
            },
            {
                'title': 'Internal — escalated',
                'body': 'Escalated to vendor/district team for follow-up.',
                'sort_order': 10,
            },
        ]
        for s in snippets:
            _, created = CannedResponse.objects.get_or_create(title=s['title'], defaults=s)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created snippet: {s['title']}"))

        self.stdout.write(self.style.SUCCESS('Canned responses ready.'))
