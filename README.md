# Inventory Manager

Production-style warehouse inventory system: catalog, stock balances, audited movements, purchase orders, role-based access, and a JWT REST API.

## Features

- Registration, login, logout, password change, and profiles
- Roles: Admin, Staff, Viewer
- Categories, products, suppliers, warehouses
- Stock receipts, issues, and transfers (balances never edited by hand)
- Purchase orders with submit / receive / cancel
- Dashboard, search, filters, and pagination
- Django Admin
- JWT REST API with filtering, search, ordering, pagination, and OpenAPI docs
- Sample data command and automated tests

## Technology stack

- Python 3, Django, Django REST Framework
- PostgreSQL, Django ORM
- SimpleJWT, django-filter, drf-spectacular
- HTML5, CSS3, Bootstrap 5, vanilla JavaScript

## Architecture

Django project package: `config`

Apps:

- `apps.users` — custom user, profile, web auth, JWT helpers
- `apps.catalog` — categories and products
- `apps.inventory` — warehouses, balances, movements, stock services
- `apps.purchasing` — suppliers and purchase orders
- `apps.core` — dashboard, pagination, shared mixins

Business rules for stock and receiving live in services (`apps.inventory.services`, `apps.purchasing.services`) and run inside `transaction.atomic()`.

## Installation (Windows)

```powershell
cd C:\Users\user\Projects\inventory_manager
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with your PostgreSQL credentials and a unique `SECRET_KEY`.

This repository already includes a local `.env` matching:

```
DB_NAME=inventory_management
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

## PostgreSQL setup

1. Install PostgreSQL for Windows and ensure the service is running.
2. Using pgAdmin or `psql`:

```sql
CREATE DATABASE inventory_management;
```

The default `postgres` role can own this database for local development. Prefer a dedicated user in anything beyond local use.

```sql
CREATE USER inventory_app WITH PASSWORD 'choose-a-strong-password';
GRANT ALL PRIVILEGES ON DATABASE inventory_management TO inventory_app;
```

If you create a dedicated user, update `DB_USER` and `DB_PASSWORD` in `.env`.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `DEBUG` | `True` for local development |
| `SECRET_KEY` | Django secret; never commit a real production key |
| `ALLOWED_HOSTS` | Comma-separated hosts |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |
| `DB_HOST` | Hostname (`localhost`) |
| `DB_PORT` | Port (`5432`) |

`.env` is gitignored. `.env.example` lists names only.

## Database migration

```powershell
python manage.py migrate
```

## Creating a superuser

```powershell
python manage.py createsuperuser
```

Use an email address as the username field value. Superusers are treated as Admin.

## Running the development server

```powershell
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Loading sample data

```powershell
python manage.py seed_demo
```

Demo accounts:

| Role | Email | Password | Notes |
|------|-------|----------|-------|
| Admin | admin@example.com | AdminPass123! | All warehouses |
| Staff | staff@example.com | StaffPass123! | Assigned to `WH-MAIN` |
| Viewer | viewer@example.com | ViewerPass123! | Read-only |

## API documentation

Interactive OpenAPI UI (login required for schema browse, or use a JWT):

- Swagger UI: http://127.0.0.1:8000/api/docs/
- Schema: http://127.0.0.1:8000/api/schema/

Obtain a token:

```http
POST /api/auth/token/
Content-Type: application/json

{"email": "admin@example.com", "password": "AdminPass123!"}
```

Send `Authorization: Bearer <access>` on later requests.

### Endpoint summary

Auth

| Method | URL | Auth | Purpose |
|--------|-----|------|---------|
| POST | `/api/auth/register/` | Public | Create a Viewer account |
| POST | `/api/auth/token/` | Public | JWT access + refresh |
| POST | `/api/auth/token/refresh/` | Public | Refresh access token |
| GET/PATCH | `/api/auth/me/` | Authenticated | Current user / profile |
| POST | `/api/auth/change-password/` | Authenticated | Body: `old_password`, `new_password` |
| GET/POST/PATCH | `/api/users/` and `/api/users/{id}/` | Admin | User administration |

Catalog and masters (GET authenticated; writes Staff/Admin; warehouse writes Admin)

| Method | URL |
|--------|-----|
| GET/POST | `/api/categories/`, `/api/products/`, `/api/suppliers/` |
| GET/PUT/PATCH/DELETE | `/api/categories/{id}/`, `/api/products/{id}/`, `/api/suppliers/{id}/` |
| GET/POST | `/api/warehouses/` |
| GET/PUT/PATCH/DELETE | `/api/warehouses/{id}/` |

Inventory

| Method | URL | Notes |
|--------|-----|-------|
| GET | `/api/stock/` | Query `low=1`, `warehouse`, `product`, `search` |
| GET | `/api/stock/{id}/` | |
| GET/POST | `/api/movements/` | Nested `lines`; posted immediately |
| GET | `/api/movements/{id}/` | No update/delete |
| POST | `/api/movements/transfer/` | Sets type to transfer |

Purchase orders

| Method | URL |
|--------|-----|
| GET/POST | `/api/purchase-orders/` |
| GET/PATCH | `/api/purchase-orders/{id}/` (PATCH draft only) |
| POST | `/api/purchase-orders/{id}/submit/` |
| POST | `/api/purchase-orders/{id}/receive/` body `{"lines":[{"id":1,"quantity":"5"}]}` |
| POST | `/api/purchase-orders/{id}/cancel/` |

List endpoints support `search`, `ordering`, `page`, and `page_size`.

Example receipt:

```http
POST /api/movements/
Authorization: Bearer <token>
Content-Type: application/json

{
  "movement_type": "receipt",
  "warehouse": 1,
  "reference": "ASN-44",
  "notes": "",
  "lines": [{"product": 1, "quantity": "10", "unit_cost": "4.50"}]
}
```

Typical statuses: 200, 201, 400, 401, 403, 404, 409.

## Testing

```powershell
python manage.py test
```

## Project structure

```
inventory_manager/
  config/           settings, root URLs, API router
  apps/core|users|catalog|inventory|purchasing
  templates/        Django templates (Bootstrap 5)
  static/           CSS / JS
  media/            uploaded avatars
  manage.py
  requirements.txt
```

## User roles

- **Admin** — all data, user management, warehouses
- **Staff** — mutate catalog/POs/movements for **assigned warehouses**
- **Viewer** — read-only (except own profile/password)

Authorization is enforced in views, DRF permissions, and stock/PO services.

## Important commands

```powershell
python manage.py check
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py test
python manage.py runserver
```

## Troubleshooting

- **Could not connect to PostgreSQL** — start the PostgreSQL Windows service; confirm `DB_HOST`/`DB_PORT` and that `inventory_management` exists.
- **password authentication failed** — match `DB_USER`/`DB_PASSWORD` to your local Postgres role.
- **SECRET_KEY is not set** — copy `.env.example` to `.env`.
- **relation does not exist** — run `python manage.py migrate`.
- **Staff cannot post stock** — assign warehouses on the user (web Users page or Admin).
- **Insufficient stock** — issues/transfers cannot exceed on-hand quantity.
- **JWT 401** — send `Authorization: Bearer ...` and use `email` (not `username`) on `/api/auth/token/`.
