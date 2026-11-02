# Error Codes to UI Behavior

Branch on `error`; never use localized `message` as program logic. Do not expose stack traces, SQL, or internal paths.

| Error | HTTP | UI behavior |
|---|---:|---|
| `INVALID_CREDENTIALS` | 401 | Login form error; do not reveal whether username exists. |
| `ACCOUNT_LOCKED` | 403 or contract-defined | Login form explains account is locked; confirm exact status in OpenAPI. |
| `TOKEN_EXPIRED`, `UNAUTHORIZED` | 401 | Clear token/cache and return to login. |
| `FORBIDDEN` | 403 | Show access error; keep session. |
| `VALIDATION_ERROR` | 400 | Map `details[].field` to form fields; remaining details to form summary. |
| `CLASS_FULL` | 409 | Explain full class and refetch sections. |
| `ALREADY_REGISTERED` | 409 | Explain existing registration and refetch registration/sections. |
| `SAME_SUBJECT_REGISTERED` | 409 | Explain subject already selected; refetch. |
| `STUDENT_SCHEDULE_CONFLICT` | 409 | Explain schedule conflict; refetch; show conflicting section only if response details identify it. |
| `CREDIT_LIMIT_EXCEEDED` | 409 | Explain the semester maximum and current credits from `details[]`; keep the registration and seat count unchanged. |
| `CREDIT_LIMIT_BELOW_MIN` | 409 | Explain that cancellation would go below the minimum; keep the registration and seat count unchanged. |
| `DUPLICATE_CODE` | 409 | Map field if `details[].field` is present; preserve other input. |
| `SCHEDULE_CONFLICT` | 409 | Show backend details in section form; do not parse `message` for logic. |
| `CAPACITY_BELOW_ENROLLMENT` | 409 | Keep edit form open and identify capacity field when details allow. |
| `SECTION_HAS_REGISTRATIONS` | 409 | Prevent delete completion and explain the section has registrations. |
| `SECTION_HAS_ACADEMIC_RECORDS` | 409 | Prevent deleting a section that has attendance or grade configuration/history. |
| `GRADE_COMPONENTS_LOCKED` | 409 | Explain grade columns cannot change after scores have been entered. |
| `SUBJECT_HAS_SECTIONS` | 409 | Prevent delete completion and explain the subject has sections. |
| `INVALID_WEEK` | 400 | Show week validation and return to a valid/current week when known. |
| HTTP 404 | 404 | Show item/page not found and offer return to list. |
| HTTP 500/unknown | 500/other | Generic retryable message; no technical details. |

The status for `ACCOUNT_LOCKED` and exact `details[]` shape must be confirmed against OpenAPI; the table does not override the contract.