# Quy ước API FE-BE

Resource objects (subject, section, semester) expose `id` in responses; `subjectId`, `sectionId`, and `semesterId` are request references/query parameters. Keep frontend types aligned with `contracts/api-types.ts`.

Quy ước này được cập nhật sau tài liệu thiết kế và được ưu tiên khi có mâu thuẫn. `contracts/openapi.yaml` là nguồn schema cuối cùng trong repository.

## JSON và HTTP

- Tất cả API dùng gốc `/api`, không đánh số version.
- JSON key camelCase; enum UPPER_SNAKE_CASE; field không áp dụng gửi/trả `null`, không bỏ field.
- Danh sách dùng envelope `{ "items": [...] }`. Subjects và sections có pagination `page`, `size`, `sort`.
- Ngày `yyyy-MM-dd`; datetime ISO 8601 với offset `+07:00`.
- Khi ghi dùng khóa ngoại `xxxId`; khi đọc có thể trả object lồng nhau, ví dụ `subject: {...}`.
- Lỗi: `{status, error, message, details[], path, timestamp}`. UI branching theo `error`, không theo `message`.
- HTTP: 400 validation, 401 chưa xác thực, 403 không đủ quyền, 404 không tìm thấy, 409 xung đột nghiệp vụ, 500 lỗi hệ thống.

## Xác thực

- Login: `POST /api/auth/login`; current user: `GET /api/auth/me`; logout `POST /api/auth/logout` là tùy chọn.
- JWT chứa `userId`, `role`, sống 3600 giây, không refresh. Gửi `Authorization: Bearer <token>`.
- `/me` dùng danh tính từ token; không gửi studentId/lecturerId trên client.
- HTTP 401 xóa token và về login; HTTP 403 chỉ thông báo, không logout.

## Endpoint được nêu

| Method/path | Mục đích / quyền |
|---|---|
| `POST /api/auth/login` | Xác thực |
| `GET /api/auth/me` | Tài khoản hiện tại |
| `POST /api/auth/logout` | Tùy chọn |
| `GET /api/subjects` | Tra cứu công khai danh mục môn học |
| `POST/PUT/DELETE /api/subjects` | Quản lý môn học, ADMIN |
| `/api/sections` | CRUD lớp; danh sách yêu cầu `semesterId`, ADMIN CRUD |
| `GET /api/sections/lookups` | Lookup cho form lớp |
| `GET /api/sections/{id}/students` | ADMIN hoặc giảng viên phụ trách |
| `GET /api/semesters`, `GET /api/semesters/current` | Học kỳ và `currentWeek` |
| `POST /api/registrations` | Đăng ký với body `{ "sectionId": ... }` |
| `DELETE /api/registrations/{id}` | Hủy đăng ký của mình |
| `GET /api/registrations/me?semesterId=` | Đăng ký của sinh viên hiện tại |
| `GET /api/students/me/timetable` | Thời khóa biểu sinh viên, query `semesterId`, `week` |
| `GET /api/lecturers/me/timetable` | Lịch giảng viên, query `semesterId`, `week` |
| `GET /api/lecturers/me/sections` | Lớp của giảng viên hiện tại |
| `POST /api/timetable/check` | Kiểm tra xung đột thời khóa biểu, không ghi dữ liệu |
| `GET /api/tuition/me` | Sinh viên xem hóa đơn học phí, query `semesterId` tùy chọn |
| `POST /api/tuition/me/payments` | Sinh viên thanh toán theo đợt/toàn bộ, yêu cầu `idempotencyKey` |
| `GET /api/receipts/me`, `GET /api/receipts/{receiptId}` | Danh sách/chi tiết biên lai của chính sinh viên |
| `GET /api/receipts/{receiptId}/pdf` | Tải PDF biên lai; chỉ chủ biên lai hoặc ADMIN |
| `/api/admin/tuition-rates` | ADMIN quản lý đơn giá theo học kỳ, khóa/ngành, khoảng hiệu lực |
| `/api/admin/tuition/discounts` | ADMIN cấp/thu hồi miễn giảm học phí |
| `/api/admin/tuition/installments` | ADMIN cấu hình các đợt nộp theo học kỳ |
| `/api/admin/tuition/invoices` | ADMIN tạo, liệt kê hóa đơn và xem báo cáo học phí |

`GET /api/sections` trả `remainingSeats`, `full`, `registeredByMe`. Request/response schemas, verbs CRUD còn thiếu phải đọc từ OpenAPI, không suy đoán.

Học phí được tính theo TCHP và đơn giá có hiệu lực tại ngày bắt đầu học kỳ. Thanh toán giả lập có tính idempotent; biên lai giữ snapshot bất biến để tải lại PDF. Đơn giá/miễn giảm trong seed chỉ là dữ liệu kiểm thử, không phải mức thu chính thức.
