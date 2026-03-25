# DistrictDesk — System Architecture Design

**Project:** DistrictDesk  
**Document:** System Architecture Design 
**Author:** David Gosney  

---

## 1. Overview

DistrictDesk is a web-based IT operations platform built with **Django** (backend), **PostgreSQL** (database), and server-rendered templates with **Chart.js** for analytics. This document describes the high-level architecture, component layers, Django app structure, and data flow to support the functional requirements and 25-week development plan.

---

## 2. Architectural Style

- **Layered (multi-tier) web application:** presentation → business logic → data access → database.
- **Request/response:** synchronous HTTP; no real-time requirements for the initial scope.
- **Single deployment unit:** one Django project deployed to a single server or platform (e.g. VM, PaaS), with PostgreSQL as a separate service.

---

## 3. High-Level Architecture Diagram (Conceptual)

```
                    +------------------+
                    |   Web Browser    |
                    |  (Staff / Admin) |
                    +--------+---------+
                             |
                             | HTTPS
                             v
                    +------------------+
                    |  Web Server      |
                    |  (e.g. Gunicorn  |
                    |   + Nginx)       |
                    +--------+---------+
                             |
                             v
    +------------------------------------------------------------------------+
    |                     Django Application Layer                           |
    +------------------------------------------------------------------------+
    |  +-------------+  +-------------+  +-------------+  +---------------+  |
    |  |   URLs /    |  |   Views     |  |  Forms &    |  |  Middleware   |  |
    |  |   Routing   |  |   (logic)   |  |  Validation |  |  (Auth, RBAC) |  |
    |  +-------------+  +-------------+  +-------------+  +---------------+  |
    |  +-------------+  +-------------+  +-------------+                     |
    |  |  Templates  |  |  Django ORM |  |  Auth       |                     |
    |  |  (HTML+JS)  |  |  (models)  |  |  (sessions) |                     |
    |  +-------------+  +-------------+  +-------------+                     |
    +------------------------------------------------------------------------+
                             |
                             | SQL (connection)
                             v
                    +------------------+
                    |   PostgreSQL     |
                    |   Database       |
                    +------------------+
```

---

## 4. Component Layers

### 4.1 Presentation Layer

- **Technology:** Django templates (Jinja2-style), CSS, JavaScript (vanilla or minimal), Chart.js for dashboards (FR-31–FR-35).
- **Responsibilities:**
  - Render HTML pages (login, ticket list/detail, device list, admin dashboards).
  - Form rendering and client-side validation where helpful.
  - Charts for ticket volume, categories, resolution time, device counts.
- **Access control:** Views render different content or redirect based on role (Standard User vs Administrator); no sensitive admin data in responses for standard users.

### 4.2 Application (Business) Layer

- **Technology:** Django views (function- or class-based), forms, custom middleware.
- **Responsibilities:**
  - **Authentication (FR-1–FR-4):** Login, logout, password reset using Django auth.
  - **Authorization (FR-5–FR-9):** Role-based checks before serving ticket management, device inventory, dashboards, and user/category/priority configuration.
  - **Ticket workflow:** Create (FR-10–FR-13), list/detail (FR-14–FR-17), assign/update/comment/close (FR-18–FR-22), search/filter/sort (FR-23–FR-25).
  - **Device CRUD and assignment (FR-26–FR-29),** and linking tickets to devices (FR-30).
  - **Activity logging:** On status change and assignment, write to TicketStatusHistory and TicketAssignment (FR-36–FR-37).
  - **Admin management:** User CRUD and deactivation (FR-38), category and priority configuration (FR-39).
  - **Analytics:** Queries and aggregations for dashboards (FR-31–FR-35); no separate service in v1.

### 4.3 Data Access Layer

- **Technology:** Django ORM and migrations.
- **Responsibilities:**
  - Map Python models to PostgreSQL tables per the Database Schema document.
  - Encapsulate queries (filters, ordering, aggregates) used by views.
  - Enforce integrity via model constraints and validation.

### 4.4 Data Layer

- **Technology:** PostgreSQL.
- **Responsibilities:** Persist users, roles, tickets, assignments, comments, status history, devices, locations, and configurable lookups (categories, priorities). Indexes and constraints as defined in the schema.

---

## 5. Django Project Structure

Recommended layout for the codebase:

```
districtdesk/                    # Project root (repository root)
├── config/                      # Django project package
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py              # Shared settings
│   │   ├── development.py      # Local dev, DEBUG=True
│   │   └── production.py       # Production, DEBUG=False, allowed hosts
│   ├── urls.py                  # Root URLconf
│   ├── wsgi.py
│   └── asgi.py
├── accounts/                    # User and role management
│   ├── models.py                # User (AbstractUser), Role
│   ├── views.py                 # Login, logout, password reset, profile
│   ├── urls.py
│   ├── forms.py
│   └── decorators.py            # @admin_required, @login_required usage
├── core/                        # Shared models and utilities
│   ├── models.py                # Location
│   ├── utils.py                 # Helpers if needed
│   └── (views/urls if any)
├── tickets/                     # Ticket lifecycle and related
│   ├── models.py                # TicketCategory, PriorityLevel, Ticket,
│   │                            # TicketAssignment, TicketComment, TicketStatusHistory
│   ├── views.py                 # List, create, detail, update, assign, comment
│   ├── urls.py
│   ├── forms.py
│   └── services.py              # Optional: status change + history, assignment logic
├── devices/                     # Device inventory
│   ├── models.py                # DeviceType, DeviceStatus, Device
│   ├── views.py                 # List, create, update, assign
│   ├── urls.py
│   └── forms.py
├── dashboard/                   # Admin dashboards and analytics
│   ├── views.py                 # Dashboard view, analytics queries
│   ├── urls.py
│   └── (templates with Chart.js)
├── templates/                   # Global templates
│   ├── base.html
│   ├── registration/            # Login, logout, password reset
│   └── ...
├── static/
│   ├── css/
│   ├── js/                      # Chart.js, custom scripts
│   └── ...
├── docs/                        # Design and requirements
│   ├── DATABASE_SCHEMA.md
│   └── SYSTEM_ARCHITECTURE.md
├── manage.py
├── requirements.txt
└── README.md
```

- **config:** Central configuration and URL routing.
- **accounts:** Authentication and role-based identity; single source for “current user” and role checks.
- **core:** Shared entities (e.g. Location) used by tickets and devices.
- **tickets:** All ticket-related models and workflows; can call into a small `services` module for status/assignment history to keep views thin.
- **devices:** Device inventory and assignment; used by tickets via FK.
- **dashboard:** Read-only aggregations and charts for admins (FR-31–FR-35).

---

## 6. Request Flow Examples

### 6.1 Standard User Submits a Ticket (FR-10–FR-13)

1. User requests `GET /tickets/new/`; middleware ensures user is authenticated.
2. View checks role: Standard User allowed; load categories and priorities from DB.
3. View returns form (template + context).
4. User submits `POST /tickets/new/` with title, description, category, priority, optional fields.
5. View validates form, creates `Ticket` with `submitter_id=request.user`, `created_at=now`, and first `TicketStatusHistory` (e.g. Open).
6. Redirect to ticket detail; response shows confirmation.

### 6.2 Administrator Assigns a Ticket (FR-18, FR-37)

1. Admin requests ticket detail; view ensures user is Administrator and loads ticket (and current assignment if any).
2. Admin submits assignment form (choose IT user); `POST` to e.g. `/tickets/<id>/assign/`.
3. View creates/updates `TicketAssignment` and updates ticket status if needed; creates `TicketStatusHistory` for status change (FR-36).
4. Redirect back to ticket detail; response shows new assignee and history.

### 6.3 Dashboard Analytics (FR-31–FR-35)

1. Admin requests dashboard URL; view checks Administrator role.
2. View (or thin service layer) runs ORM aggregations: tickets by status, by category, by time range; resolution time; device counts by type/status.
3. View passes counts and time-series data to template; template uses Chart.js to render charts.
4. Response returns HTML with embedded data (or optional JSON endpoint for Chart.js if preferred).

---

## 7. Security and Access Control

- **Authentication:** Django `SessionAuthentication` (or other auth backends as needed); login required for all non-public pages (FR-3).
- **Authorization:** Role stored on user (e.g. `User.role`); decorators or mixins such as `@admin_required` or `UserPassesTestMixin` on views that manage all tickets (FR-7), devices (FR-8), dashboards (FR-9), or user/category/priority config (FR-38–FR-39). Standard users only see and create their own tickets (FR-6).
- **Data isolation:** Ticket list views for standard users filter by `submitter=request.user`; admin views use unfiltered (or filter-only) querysets.
- **Passwords:** Stored hashed via Django; password reset (FR-4) via Django’s built-in flow (email with secure token).
- **HTTPS:** Enforced in production (handled by reverse proxy/configuration).

---

## 8. Deployment Architecture (Target)

- **Application server:** Gunicorn (or uWSGI) running the Django WSGI app.
- **Reverse proxy:** Nginx (or similar) for static files and proxying to Gunicorn.
- **Database:** PostgreSQL on same host or separate instance; connection via Django `DATABASES` (env-based credentials).
- **Environment:** Settings split into `development` and `production`; secrets and `ALLOWED_HOSTS` in environment variables.
- **Single-node:** One app server and one DB sufficient for initial scope and demo; scaling can be addressed later if needed.

---

## 9. Traceability to Requirements and Phases

| Phase / area        | Architecture elements |
|---------------------|------------------------|
| Auth (FR-1–FR-4)    | accounts app, Django auth, login/logout/reset views |
| RBAC (FR-5–FR-9)    | Role on User, middleware/decorators, view-level checks |
| Tickets (FR-10–FR-25)| tickets app, forms, list/detail/create/update/assign/comment views, filters and search in views |
| Activity (FR-36–FR-37)| TicketStatusHistory and TicketAssignment writes in ticket views/services |
| Devices (FR-26–FR-30)| devices app, device CRUD and assignment, ticket.device_id |
| Dashboards (FR-31–FR-35)| dashboard app, aggregation queries, Chart.js in templates |
| Admin config (FR-38–FR-39)| accounts user management views, tickets category/priority admin or custom views |

This architecture supports the initial functional requirements and aligns with the proposed 25-week plan (core functionality in Phase 2, expansion in Phase 3, refinement in Phase 4).
