"""Optional ticket file attachments on create and authenticated download."""
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from accounts.models import Role
from tickets.models import Ticket, TicketAttachment, TicketCategory, PriorityLevel

User = get_user_model()


class TicketAttachmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = TicketCategory.objects.create(name='Hardware', sort_order=0)
        cls.pri = PriorityLevel.objects.create(name='Medium', sort_order=1)
        cls.role_std, _ = Role.objects.get_or_create(name='Standard User')
        cls.role_admin, _ = Role.objects.get_or_create(name='Administrator')

    def setUp(self):
        self.user_std = User.objects.create_user(
            username='att1@example.com',
            email='att1@example.com',
            password='pass12345',
        )
        self.user_std.role = self.role_std
        self.user_std.save()
        self.user_other = User.objects.create_user(
            username='att2@example.com',
            email='att2@example.com',
            password='pass12345',
        )
        self.user_other.role = self.role_std
        self.user_other.save()
        self.user_adm = User.objects.create_user(
            username='attadm@example.com',
            email='attadm@example.com',
            password='pass12345',
        )
        self.user_adm.role = self.role_admin
        self.user_adm.save()

    def _ticket_post_data(self):
        return {
            'title': 'Attachment test',
            'description': 'See attached file.',
            'category': self.cat.pk,
            'priority': self.pri.pk,
        }

    def test_create_ticket_without_attachments(self):
        self.client.login(username='att1@example.com', password='pass12345')
        r = self.client.post('/tickets/new/', self._ticket_post_data())
        self.assertEqual(r.status_code, 302)
        ticket = Ticket.objects.get(title='Attachment test')
        self.assertEqual(ticket.attachments.count(), 0)

    def test_create_ticket_with_pdf_attachment(self):
        self.client.login(username='att1@example.com', password='pass12345')
        pdf = SimpleUploadedFile(
            'screenshot.pdf',
            b'%PDF-1.4 minimal',
            content_type='application/pdf',
        )
        data = self._ticket_post_data()
        r = self.client.post('/tickets/new/', {**data, 'attachments': pdf})
        self.assertEqual(r.status_code, 302)
        ticket = Ticket.objects.get(title='Attachment test')
        self.assertEqual(ticket.attachments.count(), 1)
        att = ticket.attachments.first()
        self.assertEqual(att.original_filename, 'screenshot.pdf')
        self.assertGreater(att.size_bytes, 0)

    def test_create_ticket_rejects_exe(self):
        self.client.login(username='att1@example.com', password='pass12345')
        bad = SimpleUploadedFile('virus.exe', b'MZ', content_type='application/octet-stream')
        data = self._ticket_post_data()
        data['title'] = 'Bad file ticket'
        r = self.client.post('/tickets/new/', {**data, 'attachments': bad})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Ticket.objects.filter(title='Bad file ticket').exists())

    @override_settings(TICKET_ATTACHMENT_MAX_BYTES=100)
    def test_create_ticket_rejects_oversized_file(self):
        self.client.login(username='att1@example.com', password='pass12345')
        big = SimpleUploadedFile('big.txt', b'x' * 200, content_type='text/plain')
        data = self._ticket_post_data()
        data['title'] = 'Big file ticket'
        r = self.client.post('/tickets/new/', {**data, 'attachments': big})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Ticket.objects.filter(title='Big file ticket').exists())

    def test_detail_shows_attachment_link(self):
        ticket = Ticket.objects.create(
            title='Has file',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.user_std,
        )
        TicketAttachment.objects.create(
            ticket=ticket,
            file=SimpleUploadedFile('note.txt', b'hello', content_type='text/plain'),
            original_filename='note.txt',
            content_type='text/plain',
            size_bytes=5,
            uploaded_by=self.user_std,
        )
        self.client.login(username='att1@example.com', password='pass12345')
        r = self.client.get(f'/tickets/{ticket.pk}/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'note.txt')
        self.assertContains(r, '/tickets/attachments/')

    def test_download_forbidden_for_other_user(self):
        ticket = Ticket.objects.create(
            title='Private file',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.user_std,
        )
        att = TicketAttachment.objects.create(
            ticket=ticket,
            file=SimpleUploadedFile('secret.txt', b'hidden', content_type='text/plain'),
            original_filename='secret.txt',
            content_type='text/plain',
            size_bytes=6,
            uploaded_by=self.user_std,
        )
        self.client.login(username='att2@example.com', password='pass12345')
        r = self.client.get(f'/tickets/attachments/{att.pk}/download/')
        self.assertEqual(r.status_code, 404)

    def test_download_ok_for_submitter(self):
        ticket = Ticket.objects.create(
            title='My file',
            description='d',
            category=self.cat,
            priority=self.pri,
            status=Ticket.Status.OPEN,
            submitter=self.user_std,
        )
        att = TicketAttachment.objects.create(
            ticket=ticket,
            file=SimpleUploadedFile('mine.txt', b'data', content_type='text/plain'),
            original_filename='mine.txt',
            content_type='text/plain',
            size_bytes=4,
            uploaded_by=self.user_std,
        )
        self.client.login(username='att1@example.com', password='pass12345')
        r = self.client.get(f'/tickets/attachments/{att.pk}/download/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'data', b''.join(r.streaming_content))
