# Frontend Rules

- Stack: React, TypeScript, Vite, Ant Design, React Router, Axios, TanStack Query.
- Feature code belongs in `src/modules/{auth,catalog,registration,timetable}`. App routing/layout belongs in `src/app`; reusable API/UI/hooks/utils belong in `src/shared`.
- The API client base URL defaults to `/api`. Keep endpoint paths relative to that base.
- Single active registration semester: registration, timetable, and section views auto-bind to it; public course catalog and admin catalog pages read/write through the shared catalog API and server contract.
- Roster student table is implemented in `SectionRosterPage` for UC003/UC009.
- Lecturer section pages provide attendance entry, gradebook entry, and Excel downloads through the academic-records API. Backend authorization is authoritative: a lecturer may manage records only for assigned sections.
- Student registration supports cancellation and changing to another section of the same subject; the backend remains authoritative for credit limits, schedule checks, capacity, and atomicity.
- Do not guess API fields. Use types aligned with `contracts/openapi.yaml` and `contracts/api-types.ts`.
- Parse API failures using `error`, not `message`. Map `VALIDATION_ERROR` details to fields.
- Never calculate or optimistically mutate enrollment counts. Refetch after successful writes.
- 401 clears session; 403 does not log out. Route visibility is UX only; the server enforces RBAC.
- Build and local-run commands are documented in `README.md` and `frontend/README.md`. Add focused tests with module changes.
