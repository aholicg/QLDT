# Backend Rules

- Runtime: Python 3.12+, FastAPI, SQLAlchemy 2, and Alembic; application package root is `app/`.
- Start locally with `uvicorn app.main:app --reload` from `backend/`.
- Authentication reads the canonical MySQL `USERS` table; production code must not fall back to fixture/mock users.
- `db/schema.sql` and `db/seed/seed.sql` remain the database source of truth. ORM table identifiers and Alembic migrations must preserve their uppercase names and use database `qldt`.
- Keep one ADMIN seed account only. Sample credentials are documented in `db/README.md`.
- JWT access token lifetime is 3600 seconds; do not add refresh tokens unless the SRS/API contract changes.
- `JWT_SECRET` is required and must be at least 32 characters. Semester credit limits are system-wide environment settings (`MIN_CREDITS_PER_SEMESTER=12`, `MAX_CREDITS_PER_SEMESTER=24` by default); maximum must be >= 1 and >= minimum. These are temporary defaults pending group confirmation.
- The system operates on a single active registration semester (`2026.1`); endpoints default `semesterId` to it if omitted. Registration, cancellation, and section changes lock the student's row with `SELECT ... FOR UPDATE`; capacity changes use atomic conditional updates. Prerequisite and co-requisite checks are excluded.
- All API routes use `/api`; JSON keys are camelCase and errors use the shared FE-BE envelope. Auth returns `accessToken` and a nested `user` object for FE compatibility.
- Business modules belong in `app/{controller,service,repository,entity,dto}/{auth,catalog,registration,timetable}`; shared configuration and errors belong in `app/core/`, and authentication helpers belong in `app/security/`.
- Catalog, registration, roster, and timetable services for UC002-UC009 are implemented with automated test coverage. Registration and cancellation enforce credit limits, ownership, and atomic capacity updates. UC006 section changes allow only another section of the same subject and semester; a failed change preserves the current registration.
- Security coverage includes role checks, registration ownership/IDOR protection, and preventing password/hash leakage. Continue enforcing resource ownership in backend services; frontend route visibility is not an authorization boundary.
- Academic records (UC010): only the assigned lecturer can view or update attendance and grades or export reports for a section. ADMIN configures section-specific grade columns; final grades require every component, normalize weighted scores to 10, and round to the nearest 0.5. Excel exports contain attendance and gradebook worksheets.
- Run and migration commands are documented in `README.md` and `backend/README.md`; CI also builds and smoke-tests the Compose gateway stack.
- `contracts/openapi.yaml` and `contracts/api-types.ts` are synchronized with backend routes and schemas.

Focused regression tests:
- `pytest tests/test_concurrency_and_security.py` — concurrent capacity race, IDOR, password leakage, and role escalation.
- `pytest tests/test_change_section.py tests/test_registration.py` — registration, cancellation, and atomic section changes.
- `pytest tests/test_academic_records.py` — attendance, grade calculations, lecturer ownership, export content, and authentication.

The concurrency race test uses SQLite for repeatable automated coverage. Validate locking behavior against MySQL when testing the MySQL deployment.
- Business modules belong in `app/{controller,service,repository,entity,dto}/{auth,catalog,registration,timetable,tuition}`; shared configuration and errors belong in `app/core/`, and authentication helpers belong in `app/security/`.
- Catalog, registration, roster, and timetable business services for UC002-UC009 are fully implemented with automated test coverage. Registration and cancellation enforce credit limits and atomic capacity updates.
- Run and migration commands are documented in `README.md` and `backend/README.md`; CI also builds and smoke-tests the Compose gateway stack.
- `contracts/openapi.yaml` and `contracts/api-types.ts` describe the backend routes and schemas, including timetable conflict and tuition/receipt APIs.
