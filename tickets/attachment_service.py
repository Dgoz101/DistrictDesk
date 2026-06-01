"""Persist validated ticket attachments after ticket create."""
from django.core.exceptions import ValidationError

from .attachment_validation import validate_attachment_files_or_raise
from .models import TicketAttachment


def save_ticket_attachments(*, ticket, user, files) -> int:
    """
    Create TicketAttachment rows for validated uploads.
    Raises ValidationError if any file fails validation.
    """
    uploads = [f for f in files if f and getattr(f, 'name', None)]
    if not uploads:
        return 0
    validate_attachment_files_or_raise(uploads)
    created = 0
    for f in uploads:
        TicketAttachment.objects.create(
            ticket=ticket,
            file=f,
            original_filename=f.name,
            content_type=getattr(f, 'content_type', '') or '',
            size_bytes=f.size,
            uploaded_by=user,
        )
        created += 1
    return created
