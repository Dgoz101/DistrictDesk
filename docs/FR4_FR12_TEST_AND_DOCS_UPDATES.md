# FR-4 and FR-12: test coverage and documentation updates

This note summarizes work that added automated tests for **password reset (FR-4)** and **optional ticket fields (FR-12)**, plus small documentation touch-ups.

---

## FR-4 — Password reset

**Goal:** Prove the reset flow sends a verifiable email and that a user can set a new password and sign in.

**Where:** `core/tests/test_phase1_auth.py` — class `Phase1PasswordResetFlowTests`, with:

```text
EMAIL_BACKEND = django.core.mail.backends.locmem.EmailBackend
```

**Tests:**

1. **Request:** `POST` to `/accounts/password-reset/` with the user’s email → expect redirect, one message in `mail.outbox`, body contains `/accounts/reset/…`.
2. **Confirm and login:** Parse `uidb64` and `token` from the email body, complete the reset, then `POST` to `/accounts/login/` with the new password.

**Django 5 behavior:** On the first visit to the reset link, Django stores the token in the session and **redirects** to a URL that uses the literal segment `set-password` instead of the secret token (to reduce token leakage via the `Referer` header). The integration test uses `Client.get(..., follow=True)` for the initial link, then posts to `/accounts/reset/<uidb64>/set-password/`.

**User-facing doc:** `HOW_TO_USE_DISTRICTDESK.md` §9 adds a short manual checklist for FR-4 and points to these tests.

---

## FR-12 — Optional ticket fields (device, location, contact)

**Goal:** Prove tickets can be created **with** optional `device`, `location`, and `contact_info`, and **without** them (FKs unset, empty contact string).

**Where:** `core/tests/test_phase3_tickets.py` — shared fixtures in `setUpTestData` (`Location`, `DeviceType`, `DeviceStatus`, `Device`).

**Tests:**

- **With optional fields:** `POST` `/tickets/new/` including `device`, `location`, `contact_info` → assert stored values on `Ticket`.
- **Without optional fields:** `POST` with only required fields → assert `device_id` and `location_id` are `None` and `contact_info` is empty.

**User-facing doc:** `HOW_TO_USE_DISTRICTDESK.md` §9 adds a short FR-12 subsection with the same test references.

---

## Traceability matrix

The project’s FR traceability file (`hidden/FR_TRACEABILITY.md`) was updated so **FR-4** and **FR-12** point at the new tests instead of “URL only” or “manual only” verification.

---

## How to run the relevant tests

```powershell
$env:DJANGO_USE_SQLITE = "1"
python manage.py test core.tests.test_phase1_auth.Phase1PasswordResetFlowTests core.tests.test_phase3_tickets.Phase3TicketTests.test_create_ticket_with_optional_device_location_contact core.tests.test_phase3_tickets.Phase3TicketTests.test_create_ticket_without_optional_fields
```

Or run the full suite: `python manage.py test core.tests`.
