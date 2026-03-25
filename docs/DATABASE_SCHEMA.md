# DistrictDesk — Database Schema Design

**Project:** DistrictDesk  
**Document:** Database Schema Design 
**Author:** David Gosney    

---

## 1. Overview

This schema supports the DistrictDesk functional requirements (FR-1 through FR-39) for user accounts, roles, tickets, device inventory, activity logging, and configurable lookups. The design targets **PostgreSQL** with **Django ORM**, using normalized tables and clear foreign-key relationships.

---

## 2. Entity-Relationship Summary

- **Users** have one **Role**. Users submit **Tickets** and may be **assigned** to tickets. Admins manage **Devices** and **Locations**.
- **Tickets** have category, priority, status; optional link to **Device** and **Location**; **TicketAssignment**, **TicketComment**, and **TicketStatusHistory** record workflow.
- **Devices** have type and status; optional assignment to **User** and **Location**.
- **TicketCategory** and **PriorityLevel** are configurable by admins (FR-39).

---

## 3. Table Definitions

### 3.1 User and Role

#### `auth_user` (Django built-in, extended as needed)

Use Django’s `AbstractUser` so we get secure auth (FR-1–FR-4) and a single user table. Add a role FK.

| Column         | Type         | Constraints | Notes                    |
|----------------|--------------|-------------|--------------------------|
| id             | SERIAL (PK)  |             | Django default           |
| username       | VARCHAR(150) | UNIQUE      | Can mirror email         |
| email          | VARCHAR(254) | UNIQUE      | FR-1                     |
| password       | VARCHAR(128) |             | Hashed                   |
| first_name     | VARCHAR(150) |             | Optional                 |
| last_name      | VARCHAR(150) |             | Optional                 |
| is_active      | BOOLEAN      | DEFAULT true| FR-38 deactivate         |
| is_staff       | BOOLEAN      | DEFAULT false| Django admin             |
| date_joined    | TIMESTAMPTZ  |             |                          |
| last_login     | TIMESTAMPTZ  | NULL        |                          |
| role_id        | INT          | FK → role   | FR-5, FR-6, FR-7        |

#### `core_role`

| Column | Type        | Constraints | Notes           |
|--------|-------------|-------------|-----------------|
| id     | SERIAL (PK) |             |                 |
| name   | VARCHAR(50) | UNIQUE      | e.g. Standard User, Administrator |

**Reference:** FR-5 (roles), FR-6 (standard user), FR-7 (administrator), FR-38 (user management).

---

### 3.2 Configurable Lookups (FR-39)

#### `tickets_ticketcategory`

| Column     | Type         | Constraints | Notes        |
|------------|--------------|-------------|--------------|
| id         | SERIAL (PK)  |             |              |
| name       | VARCHAR(100) | NOT NULL   | e.g. Hardware, Software, Access |
| sort_order | INT          | DEFAULT 0  | Optional display order  |

#### `tickets_prioritylevel`

| Column     | Type         | Constraints | Notes        |
|------------|--------------|-------------|--------------|
| id         | SERIAL (PK)  |             |              |
| name       | VARCHAR(50)  | NOT NULL   | e.g. Low, Medium, High, Critical |
| sort_order | INT          | DEFAULT 0  | For ordering |

---

### 3.3 Location

Used for optional ticket location (FR-12) and device assignment (FR-29).

#### `core_location`

| Column      | Type         | Constraints | Notes     |
|-------------|--------------|-------------|-----------|
| id          | SERIAL (PK)  |             |           |
| name        | VARCHAR(200) | NOT NULL   |           |
| description | TEXT         |             | Optional  |

---

### 3.4 Ticket (FR-10–FR-17, FR-30)

#### `tickets_ticket`

| Column       | Type         | Constraints   | Notes                          |
|--------------|--------------|---------------|--------------------------------|
| id           | SERIAL (PK)  |               |                                |
| title        | VARCHAR(200) | NOT NULL      | FR-11                          |
| description  | TEXT         | NOT NULL      | FR-11                          |
| category_id  | INT          | FK → ticketcategory | FR-11                   |
| priority_id  | INT          | FK → prioritylevel  | FR-11                   |
| status       | VARCHAR(50)  | NOT NULL      | FR-16; see status choices below |
| submitter_id | INT          | FK → auth_user| NOT NULL; FR-10, FR-14         |
| device_id    | INT          | FK → device   | NULL; FR-12, FR-30             |
| location_id  | INT          | FK → location | NULL; FR-12                    |
| contact_info | VARCHAR(255) | NULL         | FR-12 optional                 |
| created_at   | TIMESTAMPTZ  | DEFAULT NOW() | FR-13                          |
| updated_at   | TIMESTAMPTZ  | DEFAULT NOW() | For list sort / display        |
| closed_at    | TIMESTAMPTZ  | NULL         | When status → Resolved/Closed   |

**Status values (FR-16):** `Open`, `Assigned`, `In Progress`, `Resolved`, `Closed`. (Assigned and In Progress can be one value “Assigned/In Progress” or two; two allows finer workflow.)

**Reference:** FR-10–FR-13 (submission), FR-14–FR-17 (viewing, status), FR-30 (device link).

---

### 3.5 Ticket Assignment (FR-18, FR-37)

#### `tickets_ticketassignment`

| Column        | Type        | Constraints   | Notes              |
|---------------|-------------|---------------|--------------------|
| id            | SERIAL (PK) |               |                    |
| ticket_id     | INT         | FK → ticket   | NOT NULL           |
| assigned_to_id| INT         | FK → auth_user| NOT NULL (IT user) |
| assigned_by_id| INT        | FK → auth_user| NOT NULL (admin)   |
| assigned_at   | TIMESTAMPTZ | DEFAULT NOW()| FR-37              |

Only one “current” assignment per ticket is required; either enforce one active row per ticket in app logic or add `is_current BOOLEAN DEFAULT true` and set previous to false when reassigning.

**Reference:** FR-18 (assign to IT), FR-37 (assignment history).

---

### 3.6 Ticket Comments / Internal Notes (FR-21)

#### `tickets_ticketcomment`

| Column     | Type         | Constraints   | Notes                    |
|------------|--------------|---------------|--------------------------|
| id         | SERIAL (PK)  |               |                          |
| ticket_id  | INT          | FK → ticket   | NOT NULL                 |
| author_id  | INT          | FK → auth_user| NOT NULL                 |
| body       | TEXT         | NOT NULL      |                          |
| is_internal| BOOLEAN      | DEFAULT true  | FR-21 internal notes     |
| created_at | TIMESTAMPTZ  | DEFAULT NOW() |                          |

**Reference:** FR-21 (internal notes/comments).

---

### 3.7 Ticket Status History (FR-36, FR-17)

#### `tickets_ticketstathistory`

| Column      | Type        | Constraints   | Notes        |
|-------------|-------------|---------------|-------------|
| id          | SERIAL (PK) |               |             |
| ticket_id   | INT         | FK → ticket   | NOT NULL    |
| old_status  | VARCHAR(50) | NULL         | Null when first open     |
| new_status  | VARCHAR(50) | NOT NULL     |             |
| changed_by_id| INT        | FK → auth_user| NOT NULL   | FR-36       |
| changed_at  | TIMESTAMPTZ | DEFAULT NOW()| FR-36       |

**Reference:** FR-36 (status changes with user and timestamp), FR-17 (update history).

---

### 3.8 Device (FR-26–FR-30)

#### `devices_devicetype` (optional lookup)

| Column | Type         | Constraints | Notes              |
|--------|--------------|-------------|--------------------|
| id     | SERIAL (PK)  |             |                    |
| name   | VARCHAR(100) | NOT NULL   | e.g. Laptop, Printer |

#### `devices_devicestatus`

| Column | Type         | Constraints | Notes                          |
|--------|--------------|-------------|--------------------------------|
| id     | SERIAL (PK)  |             |                                |
| name   | VARCHAR(50)  | NOT NULL   | In-service, Checked-out, Repair, Retired (FR-28) |

#### `devices_device`

| Column          | Type         | Constraints    | Notes        |
|-----------------|--------------|----------------|-------------|
| id              | SERIAL (PK)  |                |             |
| asset_tag       | VARCHAR(50)  | UNIQUE, NOT NULL| FR-26      |
| device_type_id  | INT          | FK → devicetype| FR-26      |
| model           | VARCHAR(150) | NULL          | FR-26       |
| serial_number   | VARCHAR(100) | NULL          | FR-26       |
| status_id       | INT          | FK → devicestatus| FR-28    |
| assigned_user_id| INT          | FK → auth_user | NULL; FR-29 |
| location_id     | INT          | FK → location  | NULL; FR-29 |
| created_at      | TIMESTAMPTZ  | DEFAULT NOW() |             |
| updated_at      | TIMESTAMPTZ  | DEFAULT NOW() |             |

**Reference:** FR-26 (create device with fields), FR-27 (update), FR-28 (status), FR-29 (assign to user/location), FR-30 (tickets link via `tickets_ticket.device_id`).

---

## 4. Indexes and Constraints

- **Unique:** `auth_user.email`, `core_role.name`, `tickets_ticketcategory.name`, `tickets_prioritylevel.name`, `devices_device.asset_tag`.
- **Indexes for common queries:**
  - `tickets_ticket`: `(submitter_id)`, `(status)`, `(category_id)`, `(priority_id)`, `(created_at)`, `(updated_at)` for listing/filtering (FR-23–FR-25).
  - `tickets_ticketassignment`: `(ticket_id)`, `(assigned_to_id)` for admin filters (FR-23).
  - `tickets_ticketstathistory`: `(ticket_id)`, `(changed_at)` for history (FR-17).
  - `devices_device`: `(status_id)`, `(device_type_id)`, `(assigned_user_id)` for dashboards (FR-35).
- **FKs:** All foreign keys with `ON DELETE` behavior chosen appropriately (e.g. restrict on ticket delete if assignments exist, or cascade comment/history when ticket is deleted).

---

## 5. Django App and Model Mapping

| Django app   | Main models / tables                                      |
|--------------|------------------------------------------------------------|
| `accounts`   | Custom user (extends AbstractUser + role_id), Role         |
| `core`       | Location (shared)                                         |
| `tickets`    | TicketCategory, PriorityLevel, Ticket, TicketAssignment, TicketComment, TicketStatusHistory |
| `devices`    | DeviceType, DeviceStatus, Device                           |

Django’s `auth_user` can be replaced by `accounts.User` with `role` as FK to `accounts.Role`. Password reset (FR-4) can use Django’s built-in auth views and optional token table.

---

## 6. Traceability to Functional Requirements

| FR range     | Coverage in schema                                                                 |
|--------------|------------------------------------------------------------------------------------|
| FR-1–FR-4    | auth_user (email, password, login), password reset via Django auth                 |
| FR-5–FR-9    | core_role, role_id on user; permissions enforced in application layer             |
| FR-10–FR-13  | tickets_ticket (title, description, category, priority, optional device, location, contact, created_at) |
| FR-14–FR-17  | tickets_ticket (list/detail by submitter), status, tickets_ticketstathistory       |
| FR-18–FR-22  | tickets_ticketassignment, status/priority/category on ticket, tickets_ticketcomment, closed_at |
| FR-23–FR-25  | Indexes on ticket for filter/sort/search (search implemented in application layer)  |
| FR-26–FR-30  | devices_device, devices_devicetype, devices_devicestatus, core_location, ticket.device_id |
| FR-31–FR-35  | Aggregations/analytics from tickets_ticket and devices_device (no extra tables)     |
| FR-36–FR-37  | tickets_ticketstathistory, tickets_ticketassignment                                  |
| FR-38–FR-39  | auth_user (is_active, role), tickets_ticketcategory, tickets_prioritylevel         |

---

## 7. Optional Enhancements (Later)

- **Password reset tokens:** Use Django’s `PasswordResetTokenGenerator` and optional one-row-per-request table if not using built-in views.
- **Recurring issues / analytics:** Materialized views or periodic aggregation tables for FR-32–FR-34 if query performance demands it.
- **Audit log:** Generic table (user_id, action, model, object_id, timestamp) for broader admin auditing beyond ticket history.

This schema supports the initial functional requirements and leaves room for future refinements without breaking existing features.
