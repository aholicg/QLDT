# Task UC005: Student Registration

- Owner: Frontend
- Status: Registration flow implemented in backend; FE now has advanced catalog filters, a persistent visual cart, guarded batch submission, weekly timetable preview, and contract-correct cancellation
- Requirement: UC005, `docs/business-rules.md`, `docs/api-conventions.md`
- APIs: `GET /api/sections?semesterId=...`, `POST /api/registrations` with `{ "sectionId": ... }`, `GET /api/registrations/me?semesterId=...`
- UI acceptance: show `remainingSeats`, `full`, `registeredByMe`; filter by weekday, morning/afternoon shift, section/subject/unit keyword, availability and current schedule conflicts; add/remove persistent cart sections; show cart credits and a Monday–Saturday, period 1–12 timetable with fixed morning/afternoon rows and conflict highlighting; batch-submit existing POST registrations with per-section results; refetch after writes; map registration conflict details.
- Tests: `npm run build` passes (`tsc --noEmit` and Vite production build); backend full `pytest -q` and `ruff check app tests` pass. MySQL locking/concurrency remains unverified.
- Contract note: `contracts/openapi.yaml` and `contracts/api-types.ts` define registration identity as `Registration.id` and the nested canonical `Section`; the registration cart consumes those types directly.
