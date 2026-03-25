# DistrictDesk — User-Facing App Implementation Plan

**Project:** DistrictDesk  
**Document:** User-Facing App Implementation Plan
**Author:** David Gosney  

---

**Approach:** Server-rendered Django templates + optional Chart.js (data embedded in templates or small JSON endpoints).  
**Goal:** Deliver FR-1–FR-39 in the web UI with role-based access, aligned with the existing models and admin.

---

## Prerequisites (already in repo)

- Models: `accounts` (User, Role), `core` (Location), `devices`, `tickets`
- Settings: `config/settings/` (base, development, production)
- Health: `/health/`
- Seed commands: `seed_roles`, `seed_ticket_lookups`, `seed_device_lookups`

---

## Phase 0 — Project shell (1–2 sessions) — **done**

| Task | Details |
|------|--------|
| Static files | Ensure `static/css/app.css`, `static/js/charts.js` (placeholder). `collectstatic` in `README` for prod. |
| Templates | `templates/base.html`: viewport meta, nav, `{% block content %}`, messages (`django.contrib.messages`). |
| Root URL | `config/urls.py`: include `accounts`, `tickets`, `devices`, `dashboard`; set `path('', HomeView or redirect)`. |
| Home | Redirect unauthenticated → login; authenticated → `/tickets/` (or role-based: admin → `/dashboard/`). |
| `dashboard` app | `python manage.py startapp dashboard`; add to `INSTALLED_APPS`. |

**Deliverable:** Visiting `/` loads a styled shell; logged-out users see login path.

**Implemented:** `dashboard` app; `templates/base.html` + placeholders; `static/css/app.css`, `static/js/charts.js`; `config/urls.py` includes; `core.views.home` redirects (anonymous → login, admin → `/dashboard/`, else → `/tickets/`); `LOGIN_URL` set in `config/settings/base.py`.

---

## Phase 1 — Authentication (FR-1–FR-4) — **done**

| Task | Details |
|------|--------|
| Forms | `accounts/forms.py`: registration (email + password + optional password2); use `USERNAME_FIELD` or `email` as login. |
| `User` | On signup: assign `Role` “Standard User” (get_or_create). |
| Views | Register, Login, Logout; wire `LoginView`/`LogoutView` or function views. |
| Password reset | Include Django auth URLs; templates under `templates/registration/` (`password_reset_form.html`, etc.). |
| Settings | `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`; email backend console for dev. |
| URLs | `accounts/urls.py`: `register/`, `login/`, `logout/`, `password-reset/…` |

**Deliverable:** Create account, log in, log out, reset password (email in console in dev).

**Implemented:** `accounts/forms.py` (`RegisterForm`, `EmailLoginForm`); `accounts/views.py` (register, login, logout); password-reset views in `accounts/urls.py`; templates under `accounts/` and `registration/`; `EMAIL_BACKEND` console in `development.py`; `DEFAULT_FROM_EMAIL` in `base.py`; nav links for register / sign out.

---

## Phase 2 — RBAC helpers (FR-5–FR-9) — **done**

| Task | Details |
|------|--------|
| Helpers | `accounts/decorators.py` or `accounts/mixins.py`: `role_required(administrator=True)`, or `login_required` + `user.role.name` check. |
| `User` | Ensure `is_administrator` / `is_standard_user` match seeded role names. |
| Apply | Decorate admin-only views (devices, dashboard, all-tickets management, internal comments). |

**Deliverable:** Standard user cannot open admin URLs (403 or redirect).

**Implemented:** `accounts/mixins.py` (`AdminRequiredMixin`); `accounts/decorators.py` (`@admin_required` for function views); dashboard and device placeholder views use the mixin. Use `@admin_required` or `AdminRequiredMixin` on new admin-only ticket actions in later phases.

---

## Phase 3 — Tickets (Standard User) (FR-10–FR-17) — **done**

| Task | Details |
|------|--------|
| Forms | `tickets/forms.py`: `TicketForm` (title, description, category, priority, optional device, location, contact). |
| Create | `GET/POST /tickets/new/`; on save: set `submitter`, `status=Open`, `TicketStatusHistory` row (first transition). |
| List | `GET /tickets/` — queryset `filter(submitter=request.user)`; order by `-created_at`; pagination. |
| Detail | `GET /tickets/<id>/` — object-level permission: submitter or admin; show status + history + public comments. |
| Queries | `select_related` for category, priority, device, location. |

**Deliverable:** Standard user can submit and view own tickets with status/history visible.

**Implemented:** `tickets/forms.py` (`TicketForm`); `tickets/views.py` (`TicketListView`, `TicketCreateView`, `TicketDetailView`); `tickets/services.py` (`record_ticket_created`); URLs `/tickets/`, `/tickets/new/`, `/tickets/<id>/`; templates `ticket_list.html`, `ticket_form.html`, `ticket_detail.html`; pagination (25/page); administrators see all tickets on the list and can open any ticket detail; non-owners get 403 on detail. Some GET HTML tests skipped on Python 3.14 (Django test client quirk).

---

## Phase 4 — Tickets (Administrator) (FR-18–FR-22, FR-23–FR-25) — **done**

| Task | Details |
|------|--------|
| List | Admins see all tickets; filters: status, category, priority, assignee; sort by date, priority, status. |
| Search | `Q` on title + description (FR-25). |
| Assign | `POST` to assign; create `TicketAssignment`, set `is_current` on previous rows; optional status → Assigned/In Progress. |
| Update | Change status, priority, category; `tickets/services.py` for status changes + `TicketStatusHistory`. |
| Comments | `TicketComment` with `is_internal=True` (admin); show on detail for admins. |
| Close | Set status Resolved/Closed; `closed_at` timestamp. |

**Deliverable:** Full admin ticket workflow and search/filter.

**Implemented:** `tickets/services.py` (`apply_admin_ticket_update`, `assign_ticket`); `tickets/forms.py` (`TicketAdminUpdateForm`, `TicketAssignForm`, `TicketCommentForm`); `tickets/views.py` (admin filters/search/sort and pagination query preservation on `TicketListView`; `TicketAdminUpdateView`, `TicketAssignView`, `TicketCommentAddView`); URLs `/tickets/<id>/admin/update/`, `assign/`, `comment/`; templates `ticket_list.html` (filter row, Assigned column), `ticket_detail.html` (admin action cards); tests in `core/tests/test_phase4_admin_tickets.py` (POST-focused; optional GET search test skipped on Python 3.14 like Phase 3).

---

## Phase 5 — Devices (FR-26–FR-30) — **done**

| Task | Details |
|------|--------|
| CRUD | `devices` list, create, edit; admin-only decorator. |
| Forms | Map to `Device` + FKs to type, status, user, location. |
| Tickets | `TicketForm` device dropdown already links device to ticket (FR-30). |

**Deliverable:** Admins manage inventory; tickets can reference devices.

**Implemented:** `devices/forms.py` (`DeviceForm`); `devices/views.py` (`DeviceListView`, `DeviceCreateView`, `DeviceUpdateView` with `AdminRequiredMixin`); URLs `/devices/`, `/devices/new/`, `/devices/<id>/edit/`; templates `device_list.html`, `device_form.html`; tests in `core/tests/test_phase5_devices.py`. Ticket submission continues to use `TicketForm`’s device field (FR-30).

---

## Phase 6 — Dashboard & analytics (FR-31–FR-35) — **done**

| Task | Details |
|------|--------|
| View | `dashboard/views.py`: aggregate queries (counts by status, trends, categories, avg resolution time, device counts). |
| Charts | Pass `chart_data` as JSON in template; `static/js/charts.js` initializes Chart.js. |
| Optional | `GET /dashboard/api/summary/` returning JSON if you want lazy-loading later. |
| Access | Admin-only. |

**Deliverable:** Dashboard page with charts matching FR-31–FR-35 (as far as data allows).

**Implemented:** `dashboard/services.py` (`get_dashboard_data`: tickets by status/category, 14-day new-ticket trend, average resolution time from `closed_at` − `created_at`, device counts by type/status, KPI summary); `dashboard/views.py` (`DashboardHomeView`, `DashboardSummaryApiView`); URLs `/dashboard/`, `/dashboard/api/summary/`; template `templates/dashboard/home.html` with `json_script` payload and Chart.js (CDN); `static/js/charts.js`; tests in `core/tests/test_phase6_dashboard.py` (JSON API; HTML GET skipped on Python 3.14).

---

## Phase 7 — Administrative management (FR-38–FR-39) — **done**

| Task | Details |
|------|--------|
| FR-38 | Option A: Django admin only (already). Option B: custom user list/edit/deactivate under `/accounts/users/` (admin). |
| FR-39 | Option A: Django admin for categories/priorities. Option B: custom settings pages. |

**Deliverable:** Document in README which FRs are satisfied by admin vs custom UI.

**Implemented:** `accounts/forms.py` (`UserAdminForm`); `accounts/views.py` (`UserListView`, `UserAdminUpdateView`); URLs `/accounts/users/`, `/accounts/users/<id>/edit/`; templates `user_list.html`, `user_form.html`. `tickets/forms.py` (`TicketCategoryForm`, `PriorityLevelForm`); `tickets/settings_views.py` (settings hub, category/priority list/create/edit/delete with `ProtectedError` handling); URLs under `/tickets/settings/...`; templates in `templates/tickets/`. README section documents custom UI vs Django admin. Tests in `core/tests/test_phase7_admin_management.py`.

---

## Phase 8 — Polish & production (FR-adjacent) — **done**

| Task | Details |
|------|--------|
| Pagination | All lists; consistent page size (e.g. 25). |
| Errors | Custom 404/500 templates when `DEBUG=False`. |
| Accessibility | Labels, focus, contrast (iterate). |
| README | Document URL map, env vars, run instructions. |

**Implemented:** All list views use `paginate_by = 25` (`tickets/settings_views` category/priority lists aligned with tickets/devices/users). `templates/404.html` and `templates/500.html` extend `base.html`. `static/css/app.css`: `:focus-visible` outlines for links, buttons, nav. README: **URL map**, **environment variables** table, production static note (`collectstatic`). Tests: `core/tests/test_phase8_polish.py` (pagination assertion; custom 404 HTML test skipped on Python 3.14 like other GET HTML tests).

---

## Dependency order

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8
```

Phases 5 and 6 can overlap in time (different files) but **dashboard** should assume tickets/devices exist.

---

## Testing checklist (manual)

- [ ] Register → login as standard user → create ticket → see in list/detail.
- [ ] Login as admin → see all tickets → filter/search → assign → change status → comment → close.
- [ ] Admin devices CRUD; ticket links device.
- [ ] Dashboard loads and charts match expected aggregates.
- [ ] Standard user cannot access `/devices/` or `/dashboard/` (or admin ticket actions).

---

## Files to add (summary)

| Area | Files |
|------|--------|
| Accounts | `urls.py`, `views.py`, `forms.py`, `decorators.py` |
| Tickets | `urls.py`, `views.py`, `forms.py`, `services.py` |
| Devices | `urls.py`, `views.py`, `forms.py` |
| Dashboard | `apps.py`, `urls.py`, `views.py` |
| Config | `config/urls.py` includes |
| Templates | `base.html`, `accounts/*`, `tickets/*`, `devices/*`, `dashboard/*`, `registration/*` |
| Static | `static/css/app.css`, `static/js/charts.js` |

---

## Notes

- Run seeds after `migrate` on a fresh DB before testing registration.
- Use **SQLite** ( `DJANGO_USE_SQLITE=1` ) or **PostgreSQL** with `DJANGO_DB_*` — same code path.
- Chart.js: add via CDN in `base.html` or vendor file under `static/` for offline dev.

This plan is the single source of truth for implementing the user-facing step; update this doc if scope or FR coverage changes.
