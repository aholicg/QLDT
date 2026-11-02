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
| `SUBJECT_HAS_SECTIONS` | 409 | Prevent delete completion and explain the subject has sections. |
| `INVALID_WEEK` | 400 | Show week validation and return to a valid/current week when known. |
| `TUITION_RATE_NOT_FOUND` | 404 | Do not generate an invoice without an applicable rate; ask an administrator to configure one. |
| `INVOICE_NOT_FOUND` | 404 | Show that the requested invoice or receipt was not found. |
| `INVOICE_ALREADY_PAID` | 409 | Do not submit another payment; refetch invoice and receipts. |
| `PAYMENT_EXCEEDS_BALANCE` | 409 | Keep the payment form open and show the remaining invoice/installment balance. |
| `INVOICE_HAS_PAYMENTS` | 409 | Prevent recalculation or installment changes after payment exists. |
| `INSTALLMENT_SUM_MISMATCH` | 400 | Correct the installment percentages/amounts before saving. |
| `DISCOUNT_EXCEEDS_TOTAL` | 400 | Correct discount configuration; invoice amount cannot become negative. |
| `INVOICE_CANCELLED` | 409 | Do not accept payment for a cancelled invoice. |
| HTTP 404 | 404 | Show item/page not found and offer return to list. |
| HTTP 500/unknown | 500/other | Generic retryable message; no technical details. |

The status for `ACCOUNT_LOCKED` and exact `details[]` shape must be confirmed against OpenAPI; the table does not override the contract. Payment idempotency is scoped to the authenticated student and key.