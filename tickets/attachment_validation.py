"""Validate optional ticket file uploads (extension and size limits)."""
from __future__ import annotations

import os
from pathlib import PurePath

from django.conf import settings
from django.core.exceptions import ValidationError


def attachment_settings() -> dict:
    return {
        'max_bytes': getattr(settings, 'TICKET_ATTACHMENT_MAX_BYTES', 5 * 1024 * 1024),
        'max_files': getattr(settings, 'TICKET_ATTACHMENT_MAX_FILES', 5),
        'max_total_bytes': getattr(
            settings, 'TICKET_ATTACHMENT_MAX_TOTAL_BYTES', 15 * 1024 * 1024
        ),
        'allowed_extensions': frozenset(
            ext.lower()
            for ext in getattr(
                settings,
                'TICKET_ATTACHMENT_ALLOWED_EXTENSIONS',
                ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf', '.txt'),
            )
        ),
    }


def attachment_accept_attribute() -> str:
    exts = attachment_settings()['allowed_extensions']
    return ','.join(sorted(exts))


def attachment_help_text() -> str:
    cfg = attachment_settings()
    max_mb = cfg['max_bytes'] / (1024 * 1024)
    total_mb = cfg['max_total_bytes'] / (1024 * 1024)
    exts = ', '.join(sorted(cfg['allowed_extensions']))
    return (
        f'Optional. Up to {cfg["max_files"]} files, {max_mb:g} MB each '
        f'({total_mb:g} MB total). Allowed: {exts}'
    )


def _safe_extension(filename: str, allowed: frozenset[str]) -> str | None:
    name = os.path.basename(filename or '').strip()
    if not name or name.startswith('.'):
        return None
    path = PurePath(name)
    suffix = path.suffix.lower()
    if not suffix or suffix not in allowed:
        return None
    # Reject odd names like "file.pdf.exe" — only allow a single allowed suffix at end
    stem = path.stem.lower()
    if '.' in stem:
        return None
    return suffix


def validate_attachment_files(files) -> list[str]:
    """
    Validate uploaded files from request.FILES.getlist('attachments').
    Returns a list of human-readable error messages (empty if OK).
    """
    cfg = attachment_settings()
    allowed = cfg['allowed_extensions']
    max_bytes = cfg['max_bytes']
    max_files = cfg['max_files']
    max_total = cfg['max_total_bytes']

    uploads = [f for f in files if f and getattr(f, 'name', None)]
    if not uploads:
        return []

    errors: list[str] = []
    if len(uploads) > max_files:
        errors.append(f'You can attach at most {max_files} files per ticket.')
        return errors

    total = 0
    for f in uploads:
        ext = _safe_extension(f.name, allowed)
        if ext is None:
            errors.append(
                f'“{f.name}” is not an allowed file type. '
                f'Allowed: {", ".join(sorted(allowed))}.'
            )
            continue
        size = f.size
        if size <= 0:
            errors.append(f'“{f.name}” is empty.')
            continue
        if size > max_bytes:
            max_mb = max_bytes / (1024 * 1024)
            errors.append(f'“{f.name}” exceeds the {max_mb:g} MB per-file limit.')
        total += size

    if not errors and total > max_total:
        total_mb = max_total / (1024 * 1024)
        errors.append(f'Attachments exceed the {total_mb:g} MB total limit.')

    return errors


def validate_attachment_files_or_raise(files) -> None:
    errors = validate_attachment_files(files)
    if errors:
        raise ValidationError(errors)
