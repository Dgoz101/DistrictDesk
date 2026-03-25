# DistrictDesk

Web-based IT operations and support platform for educational environments (CSE 499 Senior Project).

## Stack

- **Backend:** Django 4.2+
- **Database:** PostgreSQL (or SQLite for local dev)
- **Docs:** `docs/DATABASE_SCHEMA.md`, `docs/SYSTEM_ARCHITECTURE.md`, `docs/SCALABILITY_AND_RELIABILITY.md`

## Setup

1. **Python 3.10+** and **pip** (and optionally **PostgreSQL**).

2. **Clone / open project** and create a virtual environment:

   ```bash
   cd DistrictDesk
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # macOS/Linux
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Database**

   - **Option A – PostgreSQL:** Create a database (e.g. `districtdesk`) and set:

     ```bash
     set DJANGO_DB_NAME=districtdesk
     set DJANGO_DB_USER=postgres
     set DJANGO_DB_PASSWORD=yourpassword
     set DJANGO_DB_HOST=localhost
     set DJANGO_DB_PORT=5432
     ```

   - **Option B – SQLite (no PostgreSQL):**

     ```bash
     set DJANGO_USE_SQLITE=1
     ```

5. **Create and run migrations:**

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Seed lookup data (roles, categories, priorities, device types/statuses):**

   ```bash
   python manage.py seed_roles
   python manage.py seed_ticket_lookups
   python manage.py seed_device_lookups
   ```

7. **Create a superuser and run the dev server:**

   ```bash
   python manage.py createsuperuser
   python manage.py runserver
   ```

   Open http://127.0.0.1:8000/admin/ and log in. Assign the **Administrator** role to your user (via the User edit page in admin) to use admin features.

## Project structure

- `config/` – Django project settings and root URLconf
- `accounts/` – User (custom), Role, auth
- `core/` – Location (shared)
- `tickets/` – Ticket, category, priority, assignment, comments, status history
- `devices/` – Device, device type, device status
- `docs/` – Database schema and system architecture

## Production and reliability

- **Settings:** Use `config/settings/base.py`, `development.py`, and `production.py`. Set `DJANGO_ENV=production` for production; set `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` (comma-separated).
- **Health check:** `GET /health/` returns 200 and `{"status": "ok", "database": "connected"}` when the app and DB are up; use for load balancers and monitoring.
- **Scalability:** See `docs/SCALABILITY_AND_RELIABILITY.md` for backups, logging, horizontal scaling, caching, and DB tuning.

## Management commands

- `seed_roles` – Create Standard User and Administrator roles
- `seed_ticket_lookups` – Create default ticket categories and priority levels
- `seed_device_lookups` – Create default device types and statuses
