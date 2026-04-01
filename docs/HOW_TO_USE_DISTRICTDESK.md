# How to use DistrictDesk

**Project:** DistrictDesk  
**Document:** How To  
**Author:** David Gosney    

---

This guide walks through everything you need to **install, configure, run, and day-to-day use** the DistrictDesk project. For a shorter overview, see the root [`README.md`](../README.md). For deeper design detail, see the other files in [`docs/`](./).

---

## 1. What you are running

DistrictDesk is a **Django 5.2** web application. You run it with **`python manage.py runserver`** for local development, or behind a production WSGI server (e.g. Gunicorn) plus a reverse proxy in deployment.

**Requirements**

- **Python** 3.10 or newer (the test suite is expected to pass on Python 3.14 with Django 5.2 LTS).
- **pip** (bundled with recent Python).
- **PostgreSQL** — optional for local work if you use **SQLite** instead.

---

## 2. Clone and open the project

From a terminal:

```bash
cd path/to/DistrictDesk
```

Use a dedicated virtual environment so dependencies do not clash with other projects.

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (cmd)**

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS / Linux**

```bash
python -m venv .venv
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## 3. How settings and environment variables work

Django loads settings from **`config.settings`**, which picks a module using **`DJANGO_ENV`**:

| `DJANGO_ENV` | Settings module | Typical use |
|----------------|-----------------|-------------|
| Unset or `development` | `config.settings.development` | Local development (`DEBUG=True`, console email) |
| `production` | `config.settings.production` | Deployed servers (`DEBUG=False`, strict secrets and HTTPS defaults) |

**Important variables**

| Variable | When it matters | Purpose |
|----------|-----------------|---------|
| `DJANGO_ENV` | Always (optional) | `development` (default) vs `production`. |
| `DJANGO_SECRET_KEY` | **Required in production** | Cryptographic signing. Must be strong and **not** the dev placeholder. |
| `DJANGO_ALLOWED_HOSTS` | **Required in production** | Comma-separated hostnames (e.g. `app.example.com,www.example.com`). In development you can override with this env var; otherwise dev allows common local hosts. |
| `DJANGO_USE_SQLITE` | Local / tests | Set to `1` to use SQLite (`db.sqlite3` in the project root) instead of PostgreSQL. |
| `DJANGO_DB_*` | PostgreSQL | `DJANGO_DB_NAME`, `DJANGO_DB_USER`, `DJANGO_DB_PASSWORD`, `DJANGO_DB_HOST`, `DJANGO_DB_PORT` when **not** using SQLite. |
| `DEFAULT_FROM_EMAIL` | Email flows | “From” address for password reset and similar mail in production. |

**PowerShell note:** Use `$env:VARIABLE = "value"` to set variables for the current session. The `set` command in cmd does **not** apply to PowerShell the same way.

---

## 4. Choose a database

### Option A — SQLite (fastest local setup)

Set once per terminal session:

**PowerShell**

```powershell
$env:DJANGO_USE_SQLITE = "1"
```

**cmd**

```cmd
set DJANGO_USE_SQLITE=1
```

The database file is created at the project root as **`db.sqlite3`** when you run migrations.

### Option B — PostgreSQL

1. Create a database (e.g. `districtdesk`).
2. Set connection variables (example):

**PowerShell**

```powershell
$env:DJANGO_DB_NAME = "districtdesk"
$env:DJANGO_DB_USER = "postgres"
$env:DJANGO_DB_PASSWORD = "yourpassword"
$env:DJANGO_DB_HOST = "localhost"
$env:DJANGO_DB_PORT = "5432"
```

Do **not** set `DJANGO_USE_SQLITE=1` when using PostgreSQL.

---

## 5. Apply migrations

From the project root (with your venv activated and database env vars set if needed):

```bash
python manage.py migrate
```

You normally do **not** need `makemigrations` unless you change models; the repo ships with migrations.

---

## 6. Seed lookup data

Run these **after** migrations so roles, ticket categories/priorities, and device types/statuses exist:

```bash
python manage.py seed_roles
python manage.py seed_ticket_lookups
python manage.py seed_device_lookups
```

This creates **Standard User** and **Administrator** roles, default ticket categories and priority levels, and default device types and statuses.

---

## 7. Create your first staff account

### Superuser (Django admin)

```bash
python manage.py createsuperuser
```

Follow the prompts. If you want to log in at `/accounts/login/` with the same identity, use an **email-like username** and set **email** to match (the README recommends aligning them).

### Administrator role in the app

The custom UI (dashboard, devices, user management, ticket settings) checks the **`Administrator`** **role**, not only `is_superuser`.

1. Start the server (next section).
2. Open **`http://127.0.0.1:8000/admin/`** and log in as the superuser.
3. Open **Users**, select your user, and assign the **Administrator** **role** (seeded by `seed_roles`).

Without that role, you still have Django admin; you will **not** get administrator-only app pages (you may see HTTP 403).

---

## 8. Run the development server

**PowerShell (SQLite example)**

```powershell
$env:DJANGO_USE_SQLITE = "1"
python manage.py runserver
```

Open **`http://127.0.0.1:8000/`**.

- **Not logged in:** home redirects to **login**.
- **Standard User:** home redirects to the **ticket list**.
- **Administrator:** home redirects to the **dashboard**.

---

## 9. Using the application (day-to-day)

### Registration and login

- **Register:** `/accounts/register/` — new users get **email as username** per project behavior.
- **Login:** `/accounts/login/`
- **Logout:** `/accounts/logout/`
- **Password reset:** `/accounts/password-reset/` and follow the steps.

In **development**, email is sent to the **console** (`EMAIL_BACKEND` console), so you can copy the reset link from the terminal. In **production**, configure real SMTP or an email backend and set **`DEFAULT_FROM_EMAIL`**.

**Manual check (FR-4):** Request a reset for a known account, confirm the email contains a link under `/accounts/reset/…`, open it (Django may redirect once to a `set-password` URL), set a new password, then log in with the new password. Automated coverage: `core/tests/test_phase1_auth.py` (`Phase1PasswordResetFlowTests`).

### New ticket — optional fields (FR-12)

On `/tickets/new/`, **device**, **location**, and **contact** are optional. Submit one ticket with all three filled and another with only title, description, category, and priority; both should succeed. Automated coverage: `core/tests/test_phase3_tickets.py` (`test_create_ticket_with_optional_device_location_contact`, `test_create_ticket_without_optional_fields`).

### Roles

- **Standard User:** create and work with **their own** tickets.
- **Administrator:** full ticket workflow for **all** tickets, **device** inventory, **dashboard** analytics, **user** list/edit (`/accounts/users/`), and **ticket settings** (categories and priorities at `/tickets/settings/`).

Authorization is enforced **in views**; the navigation bar only hides links for clarity.

### Useful URLs (see also README URL table)

| Area | Path |
|------|------|
| Home | `/` |
| Health check (JSON) | `/health/` |
| Django admin | `/admin/` |
| Tickets | `/tickets/`, `/tickets/new/`, `/tickets/<id>/` |
| Devices (admin) | `/devices/` |
| Dashboard (admin) | `/dashboard/` |
| Dashboard JSON (admin) | `/dashboard/api/summary/` |

---

## 10. Run automated tests

Tests expect **SQLite** unless you have a working PostgreSQL configured.

**PowerShell**

```powershell
$env:DJANGO_USE_SQLITE = "1"
python manage.py check
python manage.py test core.tests
```

Or with pytest (uses `config.settings.development` per `pytest.ini`):

```powershell
$env:DJANGO_USE_SQLITE = "1"
python -m pytest
```

Run one file:

```powershell
$env:DJANGO_USE_SQLITE = "1"
python -m pytest core/tests/test_phase2_rbac.py -q
```

---

## 11. Health check for monitoring

```http
GET /health/
```

Returns JSON such as `{"status": "ok", "database": "connected"}` when the app and DB are up. Use it for load balancers and uptime checks.

---

## 12. Production: minimal checklist

1. Set **`DJANGO_ENV=production`**.
2. Set a strong **`DJANGO_SECRET_KEY`** (not the development placeholder).
3. Set **`DJANGO_ALLOWED_HOSTS`** to your real hostnames.
4. Use **PostgreSQL** in production (omit `DJANGO_USE_SQLITE` or do not set it to `1`).
5. Run **`python manage.py collectstatic`** so `STATIC_ROOT` is populated; serve static files with the web server or object storage as appropriate.
6. Put the app behind **HTTPS**. If TLS terminates at a reverse proxy, ensure **`X-Forwarded-Proto: https`** is passed so Django’s secure proxy settings work (see `config/settings/production.py`).
7. Configure **email** for password reset and operational mail.

More detail: [`SCALABILITY_AND_RELIABILITY.md`](./SCALABILITY_AND_RELIABILITY.md) and the **Production Configuration** section of the root README.

---

## 13. Where to read next

| Document | Contents |
|----------|----------|
| [`README.md`](../README.md) | Project overview, URL map, env vars, testing commands |
| [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md) | Tables and relationships |
| [`SYSTEM_ARCHITECTURE.md`](./SYSTEM_ARCHITECTURE.md) | Layers and request flows |
| [`RBAC_IMPLEMENTATION_PHASES_1_2.md`](./RBAC_IMPLEMENTATION_PHASES_1_2.md) | Role-based access implementation notes |

---

