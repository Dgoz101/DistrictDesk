"""Saved ticket filters (per-admin presets, e.g. building/location)."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Role
from core.models import Location
from tickets.models import SavedTicketFilter, Ticket, TicketCategory, PriorityLevel
from tickets.saved_filter_service import default_ticket_list_url, save_ticket_filter

User = get_user_model()


class SavedTicketFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')
        cls.cat = TicketCategory.objects.create(name='Hardware', sort_order=0)
        cls.pri = PriorityLevel.objects.create(name='Medium', sort_order=1)
        cls.loc_lib = Location.objects.create(name='Library')
        cls.loc_gym = Location.objects.create(name='Gymnasium')

    def setUp(self):
        self.admin = User.objects.create_user(
            username='sf_adm@example.com',
            email='sf_adm@example.com',
            password='pass12345',
        )
        self.admin.role = self.role_admin
        self.admin.save()
        self.std = User.objects.create_user(
            username='sf_std@example.com',
            email='sf_std@example.com',
            password='pass12345',
        )
        self.std.role = self.role_std
        self.std.save()

    def _ticket(self, title, location=None):
        return Ticket.objects.create(
            title=title,
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.std,
            location=location,
        )

    def test_location_filter_on_list(self):
        self._ticket('At library', location=self.loc_lib)
        self._ticket('At gym', location=self.loc_gym)
        self.client.login(username='sf_adm@example.com', password='pass12345')
        r = self.client.get(f'/tickets/?location={self.loc_lib.pk}')
        self.assertContains(r, 'At library')
        self.assertNotContains(r, 'At gym')

    def test_admin_can_save_and_apply_filter(self):
        self._ticket('At library', location=self.loc_lib)
        self.client.login(username='sf_adm@example.com', password='pass12345')
        r = self.client.post(
            '/tickets/filters/save/',
            {
                'name': 'Library building',
                'is_default': 'on',
                'location': str(self.loc_lib.pk),
            },
        )
        self.assertEqual(r.status_code, 302)
        saved = SavedTicketFilter.objects.get(user=self.admin, name='Library building')
        self.assertTrue(saved.is_default)
        self.assertEqual(saved.params.get('location'), str(self.loc_lib.pk))
        applied = self.client.get(f'/tickets/?location={self.loc_lib.pk}')
        self.assertContains(applied, 'Library building')
        self.assertContains(applied, 'Default')

    def test_default_redirects_empty_ticket_list(self):
        save_ticket_filter(
            user=self.admin,
            name='Library',
            params={'location': str(self.loc_lib.pk)},
            is_default=True,
        )
        self.client.login(username='sf_adm@example.com', password='pass12345')
        r = self.client.get('/tickets/')
        self.assertEqual(r.status_code, 302)
        self.assertIn(f'location={self.loc_lib.pk}', r['Location'])

    def test_clear_skips_default(self):
        save_ticket_filter(
            user=self.admin,
            name='Library',
            params={'location': str(self.loc_lib.pk)},
            is_default=True,
        )
        self.client.login(username='sf_adm@example.com', password='pass12345')
        r = self.client.get('/tickets/?skip_default=1')
        self.assertEqual(r.status_code, 200)

    def test_login_redirects_to_default_filter(self):
        save_ticket_filter(
            user=self.admin,
            name='Library',
            params={'location': str(self.loc_lib.pk)},
            is_default=True,
        )
        r = self.client.post(
            '/accounts/login/',
            {'username': 'sf_adm@example.com', 'password': 'pass12345'},
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn(f'location={self.loc_lib.pk}', r['Location'])

    def test_standard_user_cannot_save_filter(self):
        self.client.login(username='sf_std@example.com', password='pass12345')
        r = self.client.post(
            '/tickets/filters/save/',
            {'name': 'Mine', 'location': str(self.loc_lib.pk)},
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(SavedTicketFilter.objects.count(), 0)

    def test_delete_and_set_default(self):
        a = save_ticket_filter(
            user=self.admin,
            name='A',
            params={'location': str(self.loc_lib.pk)},
            is_default=True,
        )
        b = save_ticket_filter(
            user=self.admin,
            name='B',
            params={'location': str(self.loc_gym.pk)},
            is_default=False,
        )
        self.client.login(username='sf_adm@example.com', password='pass12345')
        self.client.post(f'/tickets/filters/{b.pk}/set-default/')
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertFalse(a.is_default)
        self.assertTrue(b.is_default)
        self.client.post(f'/tickets/filters/{a.pk}/delete/')
        self.assertFalse(SavedTicketFilter.objects.filter(pk=a.pk).exists())

    def test_default_ticket_list_url_helper(self):
        save_ticket_filter(
            user=self.admin,
            name='Library',
            params={'location': str(self.loc_lib.pk), 'sort': 'created_at'},
            is_default=True,
        )
        url = default_ticket_list_url(self.admin)
        self.assertIsNotNone(url)
        self.assertIn(f'location={self.loc_lib.pk}', url)
