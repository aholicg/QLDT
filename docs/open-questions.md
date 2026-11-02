# Open Questions

| Topic | Current reading | Status/decision needed |
|---|---|---|
| Account creation | Supplied SRS says accounts are preloaded; no self-registration or account-management use case. | Resolved for frontend: do not build sign-up/account CRUD. Confirm if admin account management is added later. |
| Period-to-time conversion | Timetables use periods 1-12, but no official period clock table was supplied. | Open: show period numbers until the academic schedule is provided. |
| Pagination | Subjects and sections use `page`, `size`, `sort`; roster pagination was not specified. | Resolved for current APIs: subjects, sections, and admin invoice listing are paginated; roster remains as documented in OpenAPI. |
| Semester credit limits | The implementation defaults to minimum 12 and maximum 24 credits, configurable system-wide with environment variables. | Temporary values only; the group must confirm the actual minimum and maximum. |
| Prerequisite/co-requisite subjects | Not checked; the gradebook stores course-section grade components, not academic history needed to determine prerequisites. | Keep both rules out of scope unless prerequisite data and requirements are added. |

Remaining design questions: confirm timetable period boundary semantics and whether additional grade-letter/pass/fail conversions are required.

FE-BE field names must continue to follow the current OpenAPI contract and shared TypeScript types.
| Prerequisite/co-requisite subjects | Not checked. The schema has no grades table. | Team decision: keep both rules out of scope. Revisit only if the scope/schema changes. |
| Official tuition rate / discount policy | Seeded rates, discounts, and due dates are mock values for tests only. | Open: obtain approved rates, eligibility policy, and dates before production use. |
| Receipt branding and payment provider | PDF currently uses a placeholder logo and simulated payment method. | Open: provide the official logo/signature requirements and select a payment integration before production use. |

The checked-in OpenAPI contract now includes timetable conflict and tuition/receipt endpoints. Frontend alignment remains intentionally outside this task.

The exact clock times for timetable periods and official semester credit limits remain unresolved; the backend continues to expose period numbers and use the documented temporary credit defaults.
