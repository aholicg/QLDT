# Backend API – QLDT

Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · MySQL 8 · JWT + Bcrypt.

The reviewed FE-BE conventions take precedence over older design notes. The canonical SQL schema, seed, and API contract remain under `../db/` and `../contracts/`. The generated FastAPI document at `/api/openapi.json` describes the current implementation.

## Local run

For the complete local setup and terminal commands, follow the root [README](../README.md). The short backend-only sequence is below. Start MySQL from the repository root:

```powershell
docker compose up -d db
```

Then, from `backend/` (create the virtual environment and install dependencies only on first run):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload
```

Configuration is read from the repository-root `.env` (then this directory's optional `.env`)
or process environment. Copy `.env.example` to the repository root as `.env`; set both MySQL
passwords and a `JWT_SECRET` of at least 32 characters before starting Compose or the API.

- API docs: `http://localhost:8000/api/docs`
- API OpenAPI JSON: `http://localhost:8000/api/openapi.json`
- Health: `http://localhost:8000/health`

The idempotent dev seed creates `admin / admin`, `gv001 / 123456`, and `sv20210001 / 123456`.
For the canonical sample data, see `../db/README.md`; do not load both seed sources into the same
database. Never use sample credentials in production.

## Tests and migrations

From `backend/`, run:

```powershell
ruff check .
pytest
alembic upgrade head
alembic check
```

Pytest uses an in-memory SQLite database and does not require MySQL. Migration commands require a MySQL database at `DATABASE_URL`; CI runs them against MySQL 8.4. ORM and Alembic table names stay uppercase to match `db/schema.sql` on case-sensitive MySQL hosts.

Feature 10 adds `tests/test_admin_training.py` and opt-in integration tests in `tests/integration/`. Seed the deterministic dataset with `python -m scripts.seed_test_data`, then run `pytest -m integration` while MySQL, gateway, and frontend are running. Full instructions are in [../docs/testing/feature10-admin-training.md](../docs/testing/feature10-admin-training.md).

When changing entities, create and review a migration with `alembic revision --autogenerate -m "describe change"`, then verify `alembic upgrade head` and `alembic check`.

## Architecture

```
app/
├─ controller/   HTTP routes, request validation, response DTOs
├─ service/      business rules and transaction boundaries
├─ repository/   database queries
├─ entity/       SQLAlchemy mapping for the eight canonical tables
├─ dto/          input/output schemas and common responses
├─ security/     JWT, password hashing, role dependencies
└─ core/         settings, database sessions, errors, time handling
```

Keep dependencies flowing `controller → service → repository → entity`. Services own business behavior and commit writes only after successful operations.

## Current API implementation status

All UC001-UC009 business services are fully implemented and verified with automated test coverage:
- Auth & RBAC (UC001): JWT token lifecycle, bcrypt password hashing, and role-based permissions.
- Subject and Course Section management (UC002): authenticated catalog reads, admin CRUD operations, and room/lecturer schedule conflict checks.
- Section Roster (UC003, UC009): Enrolled student listings for lecturers and administrators.
- Course Registration & Cancellation (UC005, UC006): Per-student row locking (SELECT ... FOR UPDATE), atomic capacity updates, and semester credit limit enforcement. Prerequisite and corequisite checks are excluded.
- Timetable (UC007, UC008): Weekly schedule calculation for students and lecturers.
- Single Registration Semester: All services operate against a single active semester (2026.1); query parameters default to this active semester if omitted.
- Academic records (UC010): assigned lecturers record attendance by scheduled class date, enter component grades, and export attendance/gradebook workbooks. ADMIN configures section-specific grade columns; final grades use weighted normalization to 10 and nearest-0.5 rounding.

Tests and static checks (pytest, ruff check, alembic check) pass completely.

## CI/CD and local deployment

- Root [docker-compose.yml](../docker-compose.yml) starts MySQL, the backend, and the gateway.
- [../gateway/README.md](../gateway/README.md) documents gateway behavior and its smoke test.
- [.github/workflows/ci-cd.yml](../.github/workflows/ci-cd.yml) runs lint, unit tests, MySQL migrations, a Compose smoke test, and GHCR publishing. SSH deployment is opt-in.
- Production configuration is in [../docker-compose.prod.yml](../docker-compose.prod.yml); configure its required secrets on the host and GitHub Actions.
