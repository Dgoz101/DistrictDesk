# DistrictDesk — Scalability and Reliability Guide

**Project:** DistrictDesk  
**Document:** Scalability and Reliability 
**Author:** David Gosney  

This document describes how to build and operate DistrictDesk for **scalability** (handling more users and load) and **reliability** (uptime, recoverability, and operational visibility). It is organized by phase: what to do now, and what to add as you grow.

---

## 1. Reliability First

Reliability is the foundation: a system that crashes or loses data does not scale. Prioritize these before adding scaling complexity.

### 1.1 Configuration and Secrets

- **Never commit secrets.** Use environment variables (or a secrets manager in production) for:
  - `DJANGO_SECRET_KEY`
  - `DJANGO_DB_*` (database credentials)
  - Any API keys (e.g. email for password reset)
- **Separate settings by environment.** Use `config/settings/base.py`, `development.py`, and `production.py`; set `DJANGO_SETTINGS_MODULE` per environment. In production: `DEBUG = False`, strict `ALLOWED_HOSTS`, HTTPS-only.
- **Production fail-fast:** With `DJANGO_ENV=production`, `config/settings/production.py` requires non-empty `DJANGO_SECRET_KEY` (not the development placeholder) and non-empty `DJANGO_ALLOWED_HOSTS`, and sets secure cookies, HSTS, and SSL redirect. See the README **Production Configuration** section.
- **12-factor style:** One codebase, config via env; same app runs in dev and prod with different env.

### 1.2 Database Durability and Backups

- **Use PostgreSQL in production.** It is durable, supports connections from multiple app servers, and has strong backup tools.
- **Regular backups:** Schedule daily (or more frequent) PostgreSQL backups (e.g. `pg_dump` or your host’s backup feature). Test restore periodically.
- **Migrations:** Always run migrations in a controlled way (single process or deployment step); avoid long-running migrations that lock tables during peak traffic.

### 1.3 Logging and Error Handling

- **Structured logging:** Use Python’s `logging` with a consistent format (e.g. timestamp, level, message, request id). In production, send logs to a file or a log aggregator (e.g. cloud logging) rather than only stdout.
- **Avoid exposing stack traces to users.** With `DEBUG = False`, Django shows generic error pages; use a custom 500 template and optional error reporting (e.g. Sentry) to capture exceptions.
- **Health check endpoint:** Expose a simple URL (e.g. `/health/`) that returns 200 if the app can start and (optionally) if the database is reachable. Use it for load balancers and monitoring.

### 1.4 Session and State

- **Stateless app servers.** Do not store critical state only in local memory. Use the database for sessions (Django’s `django.contrib.sessions` with DB backend) so any app instance can serve any user. This is required once you run more than one app server.
- **Cache (when added):** Prefer a shared cache (e.g. Redis) so all app instances see the same cache; avoid in-process caches for shared data when scaling out.

### 1.5 Idempotency and Data Integrity

- **Ticket and device updates:** Design critical operations so repeating them (e.g. double submit) does not corrupt data. Use transactions for multi-step updates (e.g. ticket status change + status history row).
- **Constraints:** Rely on database constraints (unique, foreign key, check) in addition to application validation so the DB enforces integrity even if code has bugs.

---

## 2. Scalability: Application Layer

### 2.1 Horizontal Scaling (Multiple App Instances)

- **Run several Django app instances** behind a reverse proxy or load balancer. Each instance is a separate process (e.g. Gunicorn workers or multiple containers). The load balancer distributes requests; no sticky sessions required if sessions are in the DB.
- **Stateless + DB sessions:** As above, use database-backed sessions so any instance can serve any request.
- **File uploads:** Do not store user-uploaded files only on one server’s disk. Use object storage (e.g. S3, Azure Blob) and reference URLs, or a shared filesystem, so all instances can serve the same files.

### 2.2 Connection Pooling

- **Database connections:** Each Gunicorn worker holds a DB connection. Many workers × many instances can exhaust PostgreSQL connections. Use a connection pooler (e.g. **PgBouncer**) between the app and PostgreSQL, or a managed DB that offers connection pooling. Configure Django’s `CONN_MAX_AGE` appropriately (e.g. 60–300 seconds) to reuse connections without holding too many open.

### 2.3 Caching (When Needed)

- **Cache expensive, rarely changing data:** e.g. list of ticket categories, priority levels, device types. Django’s cache framework with a shared backend (e.g. Redis or Memcached) lets all instances share the same cache. Invalidate or use short TTLs when admins change configuration.
- **Dashboard and analytics:** Heavy aggregation queries (tickets by status, trends, resolution time) can be cached for 1–5 minutes so repeated dashboard loads do not hit the DB every time. Consider caching per-role or per-user if data is role-dependent.
- **Avoid caching per-request or highly dynamic data** that must always be fresh (e.g. “my open tickets” for the current user).

### 2.4 Async and Background Tasks (Optional)

- **Keep request/response synchronous for core flows.** Ticket submit, assign, comment, and device CRUD can remain request-driven.
- **Heavy or non-urgent work:** If you add email notifications, report generation, or bulk exports, move them to a **background task queue** (e.g. Celery with Redis or a cloud queue). The view enqueues a job and returns quickly; a worker process runs the job. This keeps the web process responsive and avoids timeouts.

---

## 3. Scalability: Database Layer

### 3.1 Query Efficiency

- **Use the indexes you defined.** The schema already indexes ticket list/filter fields (submitter, status, category, priority, created_at, updated_at) and device fields. Ensure list and filter views use these columns in `filter()`, `order_by()`, and search.
- **Avoid N+1 queries.** Use `select_related()` and `prefetch_related()` when loading tickets with category, priority, submitter, or device so each list/detail view does not trigger one query per row.
- **Pagination:** Always paginate ticket and device lists (e.g. 25–50 per page). Never load unbounded result sets.

### 3.2 Read Replicas (Advanced)

- For very high read load (e.g. many admins viewing dashboards and reports), you can add **PostgreSQL read replicas** and route read-only queries to a replica. Django’s database router and `using()` can separate reads from writes. This is optional and only needed at higher scale.

### 3.3 Schema and Migrations

- **Keep migrations small and reversible where possible.** Test migrations on a copy of production-like data before applying in production.
- **Indexes and constraints:** Add them in migrations; they are essential for both correctness and performance as data grows.

---

## 4. Deployment and Operations

### 4.1 Reverse Proxy and Static Files

- **Reverse proxy (e.g. Nginx):** Terminate HTTPS, serve static files (after `collectstatic`), proxy dynamic requests to Gunicorn. Reduces load on the app and centralizes SSL.
- **Static and media:** In production, serve `/static/` and (if any) `/media/` from the proxy or a CDN, not from Django. Use `STATIC_ROOT` and `collectstatic`.

### 4.2 Process Management

- **Use a process manager** (e.g. systemd, supervisord, or a platform like Heroku/GCP App Engine) so the app restarts on failure and starts on boot. Run Gunicorn with multiple workers (e.g. 2–4 per instance to start).

### 4.3 Monitoring and Alerts

- **Health checks:** Load balancer or orchestrator should call `/health/` and remove unhealthy instances from rotation.
- **Metrics:** Track request rate, error rate, and latency (e.g. at the reverse proxy or with Django middleware). Optionally export metrics to a monitoring system.
- **Alerts:** Get notified on repeated 5xx errors, DB connection failures, or health check failures so you can react quickly.

### 4.4 Graceful Shutdown

- **Gunicorn:** Use a graceful timeout so in-flight requests complete before the worker exits. This avoids user-visible errors during deployments.

---

## 5. Summary: What to Do When

| Stage | Focus |
|-------|--------|
| **Now (MVP / single server)** | Env-based config, PostgreSQL in prod, DB backups, DB-backed sessions, health endpoint, pagination, `select_related`/`prefetch_related`, strict `DEBUG=False` and `ALLOWED_HOSTS` in prod. |
| **Multiple users / higher load** | Split settings (base, dev, prod), add PgBouncer or managed DB pooling, cache lookups and heavy dashboard queries, background tasks for email/reports if added. |
| **Multiple app instances** | Stateless app, shared DB sessions, shared cache (Redis), file storage in object storage or shared volume, health checks for load balancer. |
| **Larger scale** | Read replicas for analytics, CDN for static assets, dedicated monitoring and alerting. |

Building with **reliability** (config, backups, logging, health checks, stateless + DB sessions) and **efficient queries** (indexes, no N+1, pagination) from the start gives you a base that scales cleanly when you add more instances, caching, and optional background workers.
