# Open Questions

| Topic | Current reading | Status/decision needed |
|---|---|---|
| Account creation | Supplied SRS says accounts are preloaded; no self-registration or account-management use case. | Resolved for frontend: do not build sign-up/account CRUD. Confirm if admin account management is added later. |
| Period-to-time conversion | Timetables use periods 1-12, but no official period clock table was supplied. | Open: show period numbers until the academic schedule is provided. |
| Pagination | Subjects and sections use `page`, `size`, `sort`; roster pagination was not specified. | Partially resolved: paginate subjects/sections; confirm roster behavior from OpenAPI. |
| Semester credit limits | The implementation defaults to minimum 12 and maximum 24 credits, configurable system-wide with environment variables. | Temporary values only; the group must confirm the actual minimum and maximum. |
| Prerequisite/co-requisite subjects | Not checked; the gradebook stores course-section grade components, not academic history needed to determine prerequisites. | Keep both rules out of scope unless prerequisite data and requirements are added. |

Remaining design questions: confirm timetable period boundary semantics and whether additional grade-letter/pass/fail conversions are required.

FE-BE field names must continue to follow the current OpenAPI contract and shared TypeScript types.