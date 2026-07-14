"""Related / duplicate ticket links on ticket detail."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import Role
from tickets.models import Ticket, TicketCategory, PriorityLevel, TicketRelation
from tickets.relation_service import link_tickets, related_ticket_rows

User = get_user_model()


class TicketRelationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')
        cls.cat = TicketCategory.objects.create(name='Hardware', sort_order=0)
        cls.pri = PriorityLevel.objects.create(name='Medium', sort_order=1)

    def setUp(self):
        self.admin = User.objects.create_user(
            username='rel_adm@example.com',
            email='rel_adm@example.com',
            password='pass12345',
        )
        self.admin.role = self.role_admin
        self.admin.save()
        self.std = User.objects.create_user(
            username='rel_std@example.com',
            email='rel_std@example.com',
            password='pass12345',
        )
        self.std.role = self.role_std
        self.std.save()

    def _ticket(self, title='Ticket', submitter=None):
        return Ticket.objects.create(
            title=title,
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=submitter or self.std,
        )

    def test_link_tickets_normalizes_pair_and_is_symmetric(self):
        a = self._ticket('A')
        b = self._ticket('B')
        # link high->low order; should store low/high by id
        if a.pk < b.pk:
            first, second = b, a
        else:
            first, second = a, b
        rel = link_tickets(
            first,
            second,
            relation_type=TicketRelation.RelationType.DUPLICATE,
            created_by=self.admin,
        )
        self.assertEqual(rel.ticket_low_id, min(a.pk, b.pk))
        self.assertEqual(rel.ticket_high_id, max(a.pk, b.pk))
        self.assertEqual(len(related_ticket_rows(a)), 1)
        self.assertEqual(len(related_ticket_rows(b)), 1)
        self.assertEqual(related_ticket_rows(a)[0]['other'].pk, b.pk)

    def test_admin_can_link_via_post(self):
        a = self._ticket('Alpha')
        b = self._ticket('Beta')
        self.client.login(username='rel_adm@example.com', password='pass12345')
        r = self.client.post(
            f'/tickets/{a.pk}/relations/add/',
            {
                'related_ticket_id': b.pk,
                'relation_type': TicketRelation.RelationType.RELATED,
                'note': 'Same printer issue',
            },
        )
        self.assertRedirects(r, f'/tickets/{a.pk}/', fetch_redirect_response=False)
        self.assertEqual(TicketRelation.objects.count(), 1)
        detail = self.client.get(f'/tickets/{a.pk}/')
        self.assertContains(detail, f'#{b.pk}')
        self.assertContains(detail, 'Beta')
        self.assertContains(detail, 'Related')
        self.assertContains(detail, 'Same printer issue')

    def test_detail_shows_links_for_submitter(self):
        a = self._ticket('Mine A')
        b = self._ticket('Mine B')
        link_tickets(
            a,
            b,
            relation_type=TicketRelation.RelationType.DUPLICATE,
            created_by=self.admin,
        )
        self.client.login(username='rel_std@example.com', password='pass12345')
        r = self.client.get(f'/tickets/{a.pk}/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Related tickets')
        self.assertContains(r, f'#{b.pk}')
        self.assertContains(r, 'Duplicate')
        self.assertNotContains(r, 'Link related ticket')

    def test_cannot_link_to_self(self):
        a = self._ticket('Solo')
        self.client.login(username='rel_adm@example.com', password='pass12345')
        r = self.client.post(
            f'/tickets/{a.pk}/relations/add/',
            {
                'related_ticket_id': a.pk,
                'relation_type': TicketRelation.RelationType.RELATED,
            },
            follow=True,
        )
        self.assertEqual(TicketRelation.objects.count(), 0)
        self.assertContains(r, 'Cannot link a ticket to itself')

    def test_admin_can_unlink(self):
        a = self._ticket('A')
        b = self._ticket('B')
        rel = link_tickets(
            a,
            b,
            relation_type=TicketRelation.RelationType.RELATED,
            created_by=self.admin,
        )
        self.client.login(username='rel_adm@example.com', password='pass12345')
        r = self.client.post(f'/tickets/{a.pk}/relations/{rel.pk}/remove/')
        self.assertRedirects(r, f'/tickets/{a.pk}/', fetch_redirect_response=False)
        self.assertEqual(TicketRelation.objects.count(), 0)

    def test_standard_user_cannot_link(self):
        a = self._ticket('A')
        b = self._ticket('B')
        self.client.login(username='rel_std@example.com', password='pass12345')
        r = self.client.post(
            f'/tickets/{a.pk}/relations/add/',
            {
                'related_ticket_id': b.pk,
                'relation_type': TicketRelation.RelationType.RELATED,
            },
        )
        self.assertEqual(r.status_code, 403)
        self.assertEqual(TicketRelation.objects.count(), 0)

    def test_relink_updates_type(self):
        a = self._ticket('A')
        b = self._ticket('B')
        link_tickets(
            a,
            b,
            relation_type=TicketRelation.RelationType.RELATED,
            created_by=self.admin,
        )
        again = link_tickets(
            b,
            a,
            relation_type=TicketRelation.RelationType.DUPLICATE,
            created_by=self.admin,
            note='Confirmed dupe',
        )
        self.assertEqual(TicketRelation.objects.count(), 1)
        self.assertEqual(again.relation_type, TicketRelation.RelationType.DUPLICATE)
        self.assertEqual(again.note, 'Confirmed dupe')
