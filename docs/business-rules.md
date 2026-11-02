# Business Rules

- Enrollment count never exceeds capacity. Backend performs atomic conditional update and transaction; frontend never increments/decrements seats locally.
- The system operates on a single active registration semester (`2026.1`). One student registers at most once per section and at most one section per subject.
- A student's registered section schedules cannot overlap.
- Total credits per semester equal the sum of `SUBJECTS.credits` for the student's registered sections. The system-wide minimum and maximum are configured by `MIN_CREDITS_PER_SEMESTER` and `MAX_CREDITS_PER_SEMESTER` (defaults 12 and 24); the maximum must be at least 1 and no lower than the minimum.
- Registration is rejected when it would exceed the semester maximum. Cancellation is rejected only when the student currently meets the minimum and cancellation would take the total below it; students currently below the minimum may cancel.
- Prerequisite and co-requisite subject rules and checks are removed from the system.
- A room or lecturer cannot have overlapping sections for the same day, periods, and weeks.
- Cancellation deletes the registration and decrements count in one backend transaction; students can only cancel their own registrations.
- Lecturers only access sections they teach. ADMIN manages subjects/sections and can view rosters.
- A subject with sections cannot be deleted; a section with registrations cannot be deleted.
- Lecturers can record attendance, enter grades, and export reports only for sections they teach.
- Attendance is recorded once per enrolled student and scheduled class date. The date must match
  the section's weekday and teaching-week range; statuses are `PRESENT`, `ABSENT`, `LATE`, or `EXCUSED`.
- ADMIN configures 1–10 grade components per section. Component weights must total exactly 100%;
  each component defines its maximum score. The configuration is locked after the first grade is saved.
- Final grades are calculated only after every component is entered, normalized to 10, weighted,
  and rounded to the nearest 0.5 with midpoint ties rounded upward.
- Academic records are retained when registrations change; a section with attendance or grade
  configuration cannot be deleted.
- `GET /api/sections` returns `remainingSeats`, `full`, and `registeredByMe`; these drive UI state but backend remains authoritative under concurrent requests.
- Frontend refreshes relevant server data after every successful write.
