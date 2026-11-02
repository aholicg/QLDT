# QLDT Frontend

React + TypeScript + Vite app. Implemented slices include the login/auth shell, student section registration/cancellation, weekly timetable, unified course and section catalogs, and lecturer section/roster views.

## Run locally

For the full FE–BE–DB setup, use the root [README](../README.md). To run the frontend by itself,
from `frontend/`:

```bash
npm install
npm run dev
```

Vite serves the app at `http://localhost:5173` and proxies `/api` to `http://127.0.0.1:8000`.
Set `VITE_API_BASE_URL` in `.env.local` only when using a different API origin; the default is `/api`.

## Structure

- `src/app`: router and application layout.
- `src/modules`: auth, catalog, registration, and timetable features.
- `src/shared`: API client and shared UI/hooks/utilities.

## Key Features

- Use the shared types from `contracts/api-types.ts`: resource objects expose `id`; request references use names such as `sectionId` and `semesterId`.

- Single active registration semester: registration, timetable, and section views auto-bind to the active semester. Course catalog reads the backend subject API; admin subject/section forms and timetable assignments persist through backend APIs.
- Roster student table is implemented in `SectionRosterPage` for UC003/UC009.
- Lecturer section pages include scheduled-session attendance and section gradebooks (UC010); ADMIN configures grade components per section, and lecturers can export attendance/grade workbooks.
- Error handling maps API error codes directly to user feedback.

## UI conventions

- Shared typography and layout tokens live in `src/styles.css`; keep font stacks, spacing, cards, tables, and form controls consistent across modules.
- The academic portal uses a restrained HUST-inspired red accent and table-first information hierarchy. Avoid module-local font overrides unless a content type needs a deliberate distinction.
