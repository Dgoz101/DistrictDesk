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

- **Backend:** Django 4.2+
- **Database:** PostgreSQL
- **Local Development Option:** SQLite

## Documentation

Additional project documentation is available in the `docs/` folder:

- `docs/DATABASE_SCHEMA.md`
- `docs/SYSTEM_ARCHITECTURE.md`
- `docs/SCALABILITY_AND_RELIABILITY.md`

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

For production, set:

```bash
set DJANGO_ENV=production
set DJANGO_SECRET_KEY=your-secret-key
set DJANGO_ALLOWED_HOSTS=yourdomain.com,localhost
```

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
