# Database Design Summary

The canonical SQL source is `db/schema.sql` and `db/seed/seed.sql`. The API's Alembic migration under `backend/migrations/` mirrors the SQL schema; keep its table names and constraints aligned. See `db/README.md` for setup instructions.

Tables: `USERS`, `STUDENTS`, `LECTURERS`, `SUBJECTS`, `SEMESTERS`, `ROOMS`, `COURSE_SECTIONS`, `REGISTRATIONS`, `ATTENDANCE_RECORDS`, `SECTION_GRADE_COMPONENTS`, and `STUDENT_GRADES`. All foreign keys use `ON DELETE RESTRICT`. Exact API field mapping belongs in `docs/naming-map.md` and must be verified against `contracts/openapi.yaml`.

## Verified schema constraints

- Account role is `ADMIN`, `LECTURER`, or `STUDENT`; status is `ACTIVE` or `LOCKED`.
- Student/lecturer/subject/semester/room/section codes are unique within their tables.
- Semester end date follows start date; number of weeks is positive. Subject credits, room capacity, and section max capacity are positive.
- `day_of_week` is 2-8; periods are 1-12; end period is not earlier than start. Start week is at least 1 and end week is not earlier than start.
- Current enrollment is between zero and max capacity. `(student_id, section_id)` registration is unique.
- Attendance is unique per `(section_id, student_id, class_date)`; a student's grade is unique per grade component.
- Grade weights and component maxima are positive; API validation requires all component weights for a section to total 100%.
- Schema alone does not enforce schedule overlap, one section per subject/semester, or all ownership policies; backend business rules remain authoritative.

Sample data currently identifies semester `2026.1` as current (`semester_id = 3`), with 100 subjects, 30 rooms, 400 sections, and 11,983 registrations.