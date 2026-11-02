# Traceability

| Source requirement/use case | API contract | Frontend route | Test status |
|---|---|---|---|
| UC001 Login/RBAC | `POST /auth/login`, `GET /auth/me` | `/login`, role routes | Implemented; auth and RBAC tests pass with SQLite fixtures; verified against local MySQL and OpenAPI. |
| UC002 Manage subjects/sections | `/subjects`, `/sections`, `/sections/lookups` | `/admin/subjects`, `/admin/sections` | Backend services and CRUD endpoints implemented; conflict checks covered by automated tests. Feature 10 adds SQLite API tests, MySQL integration tests, and a manual UI checklist in `testing/feature10-admin-training.md`. |
| UC003 Admin class roster | `GET /sections/{id}/students` | `/app/sections/:sectionId/students` | Backend roster service implemented and covered by automated tests. Feature 10 verifies the roster against MySQL registrations and the frontend route. |
| UC004 Student session/ownership | JWT, `/me` APIs | Student route guard | Implemented; token authentication and data ownership enforced at service layer. |
| UC005 Register | `GET /sections`, `POST /registrations`, `GET /registrations/me` | `/app/sections` | Registration checks duplicates, same-subject and schedule conflicts, seat capacity, maximum credits, and serializes per-student changes; covered by backend tests. |
| UC006 Cancel/change | `DELETE /registrations/{id}` | `/app/registrations` | Cancellation enforces ownership and minimum credits, then decrements enrollment; covered by backend tests. Atomic change-class API remains unspecified. |
| UC007 Student timetable | `/semesters/current`, `/students/me/timetable` | `/app/timetable` | Backend timetable service implemented with weekly date calculations and automated coverage. |
| UC008 Lecturer timetable | `/semesters/current`, `/lecturers/me/timetable`, `/lecturers/me/sections` | `/app/timetable`, `/app/sections` | Backend timetable and lecturer section services implemented and covered by tests. |
| UC009 Lecturer roster | `/lecturers/me/sections`, `/sections/{id}/students` | `/app/sections/:sectionId/students` | Backend roster service enforces lecturer ownership and is covered by tests. |
| Timetable conflict API/admin schedule validation | `POST /timetable/check`, `POST/PUT /sections` | Not changed in this task | Structured STUDENT/ROOM/LECTURER conflicts include overlapping periods/weeks; backend tests cover interval boundaries and students affected by schedule edits. |
| Tuition invoices, payments and receipts | `/tuition/me`, `/tuition/me/payments`, `/receipts/*`, `/admin/tuition/*` | Not changed in this task | Backend API/calculation tests cover access control, invoice generation, discounts, installments, payment idempotency and PDF receipts. |

Frontend paths reflect the current app routes; API paths are relative to `/api`.
