# QLDT Project Harness

## Project

Course registration and academic management system for IT3180. The repository is divided into contracts, backend, frontend, database, documentation, gateway, CI/CD, and end-to-end tests.

## Source of truth

- Read `docs/00-INDEX.md` to find the right project document.
- The supplied FE-BE API conventions take precedence over older design notes.
- `contracts/openapi.yaml` and `contracts/api-types.ts` define the official API contract and shared TypeScript types for frontend and backend.
- SQL schema and seed live under `db/`; see `db/README.md` for setup.
- Backend is FastAPI + SQLAlchemy + Alembic under `backend/app/`; migrations preserve the uppercase SQL table names in `db/schema.sql`.
- `backend/CLAUDE.md` is the backend-specific harness. Business services cover UC001-UC010; registration operates on a single active semester, enforces credit limits, and serializes registration changes. Prerequisite and corequisite checks are excluded.
- Completed backend capabilities include concurrency-safe registration/cancellation and section changes, authentication/authorization and ownership checks, and UC010 attendance, gradebook, and Excel exports. See `backend/CLAUDE.md` for implementation boundaries and focused tests.
- `docker-compose.yml` is the local stack entry point; `.github/workflows/ci-cd.yml` runs backend checks, migrations, and gateway smoke tests.

## Working rules

- Frontend lives in `frontend/`; backend work belongs to the backend owner. The API application and tests live under `backend/app/` and `backend/tests/`.
- Keep API names, camelCase JSON keys, UPPER_SNAKE_CASE enums, error codes, and `/api` base path aligned with the contract.
- The server owns registration eligibility, conflicts, and seat counts. Refetch after mutations; never adjust enrollment counts locally.
- Registration changes are atomic from the student's perspective: changing section is limited to the same subject and semester, and a failed change must preserve the existing registration and seat.
- Assigned lecturers manage attendance, grades, and exports only for their own sections; ADMIN configures section-specific grade columns.
- A 401 clears the session and returns to login. A 403 shows an access error without logging out.
- Never expose passwords, password hashes, tokens, SQL, or stack traces in UI/logs.

Run/setup commands live in `README.md`; backend/frontend-specific architecture rules live in their respective `CLAUDE.md` files.
