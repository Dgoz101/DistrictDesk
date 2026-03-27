# DistrictDesk

DistrictDesk is a web-based IT operations and support platform designed for educational environments. It provides a centralized system for managing support requests, tracking devices, organizing users and roles, and improving visibility into day-to-day IT operations.

The goal of DistrictDesk is to make IT support more organized, efficient, and easier to manage for schools and similar organizations. Instead of relying on scattered emails, verbal requests, or disconnected spreadsheets, DistrictDesk brings support workflows, device information, and administrative tools into one place. This helps teams respond to issues faster, maintain clearer records, and make better operational decisions over time.

DistrictDesk is intended for environments where technology support is essential but resources may be limited. Schools, districts, and other organizations with small IT teams often need a practical way to manage tickets, keep track of devices, and monitor recurring issues. DistrictDesk is built to support those needs with a system that is structured, scalable, and straightforward to maintain.

## What the Project Does

DistrictDesk supports core IT operations by allowing users to:

- Submit and manage IT support tickets
- Organize tickets by category, priority, and status
- Track assignments, comments, and ticket history
- Manage device records, types, and device statuses
- Support role-based access for different kinds of users
- Monitor application health through a health check endpoint
- Use either PostgreSQL or SQLite depending on deployment needs

By combining ticket management and device tracking in one application, DistrictDesk helps organizations build a clearer picture of their technical environment and support workload.

## Tech Stack

- **Backend:** Django 5.2 LTS
- **Database:** PostgreSQL
- **Local Development Option:** SQLite

## Documentation

Additional project documentation is available in the `docs/` folder:

- `docs/DATABASE_SCHEMA.md`
- `docs/SYSTEM_ARCHITECTURE.md`
- `docs/SCALABILITY_AND_RELIABILITY.md`
- `docs/USER_FACING_IMPLEMENTATION_PLAN.md` (user-facing plan; Phases 0–8 implemented)

## Roles and permissions (RBAC)

- **Administrator** — access to the **dashboard** (`/dashboard/`: ticket/device charts and KPIs; optional JSON at `/dashboard/api/summary/`), **device inventory** (list, add, edit under `/devices/`), **user management** at `/accounts/users/` (list and edit role / active status), **ticket settings** at `/tickets/settings/` (categories and priority levels CRUD), and the full ticket workflow on list/detail (assign, update status/priority/category, internal comments, search/filter/sort on the ticket list). Enforced with `accounts.mixins.AdminRequiredMixin` (class-based views) and `accounts.decorators.admin_required` (function views).
- **Standard User** — ticket flows for their own requests (Phase 3+). Cannot access administrator-only URLs (HTTP 403).

### Administrative management (FR-38–FR-39)

- **Custom app UI:** `/accounts/users/` lists users; `/accounts/users/<id>/edit/` edits role and active flag (you cannot deactivate your own account). `/tickets/settings/` links to category and priority CRUD; deleting a category or priority that is still referenced by tickets shows an error and leaves the row in place.
- **Django admin (`/admin/`):** Still available for staff operations such as password hashes, `is_staff` / superuser flags, device type/status lookups, and other model maintenance not exposed in the custom UI.

## URL map (main app routes)

| Path | Purpose |
|------|--------|
| `/` | Home (redirects by auth role) |
| `/health/` | JSON health check |
| `/admin/` | Django admin |
| `/accounts/register/`, `/accounts/login/`, `/accounts/logout/` | Registration and session auth |
| `/accounts/password-reset/`, … | Password reset flow |
| `/accounts/users/`, `/accounts/users/<id>/edit/` | User list / edit (administrators) |
| `/tickets/`, `/tickets/new/` | Ticket list and create |
| `/tickets/settings/`, `/tickets/settings/categories/…`, `/tickets/settings/priorities/…` | Ticket lookup CRUD (administrators) |
| `/tickets/<id>/`, `/tickets/<id>/admin/update/`, `/assign/`, `/comment/` | Ticket detail and admin actions |
| `/devices/`, `/devices/new/`, `/devices/<id>/edit/` | Device inventory (administrators) |
| `/dashboard/`, `/dashboard/api/summary/` | Dashboard and optional JSON summary (administrators) |

## Environment variables

| Variable | Purpose |
|----------|---------|
| `DJANGO_ENV` | `development` or `production` (selects settings module) |
| `DJANGO_SECRET_KEY` | Secret key (required in production; see `config/settings/production.py`) |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts (production; development can override) |
| `DJANGO_USE_SQLITE` | Set to `1` to use SQLite instead of PostgreSQL |
| `DJANGO_DB_NAME`, `DJANGO_DB_USER`, `DJANGO_DB_PASSWORD`, `DJANGO_DB_HOST`, `DJANGO_DB_PORT` | PostgreSQL connection when not using SQLite |
| `DEFAULT_FROM_EMAIL` | From address for outbound mail (password reset, etc.) |

Run instructions: see **Setup**, **Database Configuration**, **Run Migrations**, **Seed Initial Data**, and **Create an Admin User** above. For production, set `DJANGO_ENV=production`, a strong `DJANGO_SECRET_KEY`, and real `DJANGO_ALLOWED_HOSTS`, then run `python manage.py collectstatic` so `STATIC_ROOT` is populated behind a reverse proxy or static file server.

## Testing

Run automated checks and tests (SQLite):

**Command Prompt (`cmd.exe`):**

```bash
python manage.py check
set DJANGO_USE_SQLITE=1
python manage.py test core.tests
```

**PowerShell:** `set DJANGO_USE_SQLITE=1` does **not** set an environment variable for Python. Use:

```powershell
python manage.py check
$env:DJANGO_USE_SQLITE = "1"
python manage.py test core.tests
```

If you omit `DJANGO_USE_SQLITE`, Django uses PostgreSQL from `DJANGO_DB_*` (and tests will fail without a working password on `localhost:5432`).

The full **`core.tests`** suite (including HTML GET tests) is expected to pass on **Python 3.14** with **Django 5.2 LTS** (the 404 test uses `assertContains(..., status_code=404)` for non-200 responses).

With **`DEBUG=False`** (production), Django serves **`templates/404.html`** and **`templates/500.html`** for missing URLs and unhandled server errors, respectively.

## Requirements

- Python 3.10+
- pip
- PostgreSQL (optional, if not using SQLite)

## Setup

Clone or open the project, then create and activate a virtual environment:

```bash
cd DistrictDesk
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # macOS/Linux
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Database Configuration

### Option A – PostgreSQL

Create a PostgreSQL database, for example `districtdesk`, then set the following environment variables:

```bash
set DJANGO_DB_NAME=districtdesk
set DJANGO_DB_USER=postgres
set DJANGO_DB_PASSWORD=yourpassword
set DJANGO_DB_HOST=localhost
set DJANGO_DB_PORT=5432
```

### Option B – SQLite

For local development without PostgreSQL, use SQLite:

```bash
set DJANGO_USE_SQLITE=1
```

## Run Migrations

Create and apply migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Seed Initial Data

Seed the default lookup data:

```bash
python manage.py seed_roles
python manage.py seed_ticket_lookups
python manage.py seed_device_lookups
```

This creates:

- Standard User and Administrator roles
- Default ticket categories and priority levels
- Default device types and statuses

## Create an Admin User

Create a superuser:

```bash
python manage.py createsuperuser
```

Use the **Username** field as your sign-in email if you want to use `/accounts/login/` (e.g. set username and email to the same address). New accounts created via **Create account** always use email as the username.

Then start the development server:

```bash
python manage.py runserver
```

Open the Django admin site:

`http://127.0.0.1:8000/admin/`

Log in with your superuser account, then assign the **Administrator** role to your user through the User edit page in the admin panel to access admin-specific features.

## Project Structure

```text
config/    - Django project settings and root URL configuration
accounts/  - Custom user model, roles, and authentication
core/      - Shared models such as Location
tickets/   - Tickets, categories, priorities, assignments, comments, and status history
devices/   - Devices, device types, and device statuses
docs/      - Database schema, architecture, and scalability documentation
```

## Production Configuration

DistrictDesk supports environment-specific settings:

- `config/settings/base.py`
- `config/settings/development.py`
- `config/settings/production.py`

For production, set (see **Environment variables** for the full list):

```bash
set DJANGO_ENV=production
set DJANGO_SECRET_KEY=your-secret-key
set DJANGO_ALLOWED_HOSTS=yourdomain.com,localhost
```

After configuration, run `python manage.py collectstatic` (non-interactive deploy) so collected static files can be served efficiently.

## Health Check

DistrictDesk includes a health check endpoint:

```http
GET /health/
```

When the application and database are available, it returns:

```json
{"status": "ok", "database": "connected"}
```

This can be used with monitoring tools, uptime checks, and load balancers.

## Scalability and Reliability

For more details about deployment considerations and system reliability, see:

- `docs/SCALABILITY_AND_RELIABILITY.md`

This documentation covers topics such as:

- Backups
- Logging
- Horizontal scaling
- Caching
- Database tuning

## Management Commands

DistrictDesk includes custom management commands for initializing lookup data:

- `seed_roles` – creates Standard User and Administrator roles
- `seed_ticket_lookups` – creates default ticket categories and priority levels
- `seed_device_lookups` – creates default device types and statuses
