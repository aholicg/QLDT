# Work Board

| Area / UC | Owner | Status | Dependency / Notes |
|---|---|---|---|
| FE shell / UC001 | Frontend | Completed | Đăng nhập/xác thực khớp FastAPI `accessToken` và nested `user` |
| FE UC002 | Frontend | Completed | Catalog công khai đọc có phân trang từ BE; admin CRUD môn/lớp và chỉnh lịch phân công lưu qua API, không dùng mock |
| FE UC003/UC009 | Frontend | Completed | Bảng danh sách sinh viên của lớp học phần (`SectionRosterPage`) hiển thị MSSV, họ tên, email, khóa, ngành, thời điểm đăng ký |
| FE UC005 | Frontend | Completed | `/app/sections` có tìm kiếm/bộ lọc nâng cao, giỏ LocalStorage theo sinh viên, gửi toàn bộ đăng ký tuần tự qua POST hiện có, tổng tín chỉ và TKB dự kiến cố định Thứ 2–Thứ 7/tiết 1–12; xử lý lỗi server và refetch |
| FE UC006 | Frontend | Completed | Sửa hủy theo `Registration.id` đúng contract `/registrations/{registration_id}`, hiển thị `details[]`/lỗi điều kiện tín chỉ; trang lớp đã đăng ký có summary 12–24 TC |
| FE UC007/UC008 | Frontend | Completed | Thời khóa biểu tuần cho sinh viên và lịch giảng dạy cho giảng viên, tự động theo kỳ duy nhất |
| BE Auth / UC001 | Backend | Completed | FastAPI auth JWT, kiểm tra mật khẩu bcrypt, RBAC đầy đủ |
| BE Catalog / UC002 | Backend | Completed | CRUD môn học và lớp học phần, kiểm tra trùng lịch phòng/giảng viên |
| BE Registration / UC005, UC006 | Backend | Completed | Đăng ký/hủy học phần, khóa dòng học sinh FOR UPDATE, tính tín chỉ theo kỳ, cập nhật sĩ số nguyên tử |
| BE Timetable / UC007, UC008 | Backend | Completed | API thời khóa biểu sinh viên & lịch dạy giảng viên, tự động nhận diện tuần học |
| BE Timetable conflicts | Backend | Completed | Engine chung phân loại xung đột sinh viên/phòng/giảng viên theo tiết và tuần giao nhau; cập nhật lớp trả chi tiết sinh viên bị ảnh hưởng |
| BE Tuition & receipts | Backend | Completed | Đơn giá hiệu lực, TCHP, miễn giảm, đợt nộp, hóa đơn, thanh toán giả lập idempotent, snapshot biên lai và PDF |
| BE Roster / UC003, UC009 | Backend | Completed | API danh sách sinh viên theo lớp học phần với kiểm tra quyền truy cập |
| API/OpenAPI | Contracts | Completed | `contracts/openapi.yaml` và `contracts/api-types.ts` bao gồm routes/DTO thời khóa biểu và học phí |
| Database seed | Database | Completed | `db/seed/seed.sql` đã cập nhật 1 kỳ duy nhất (2026.1), 400 lớp học phần thuộc kỳ 2026.1 |
| Testing / Feature 10 + Tuition | Testing | Completed | Backend suite: 66 passed, 7 integration tests skipped; thêm API, PDF, tính học phí và conflict tests |
| CI/CD & Quality | DevOps | Completed | Backend pytest/Ruff pass; Alembic upgrade/check trên SQLite pass; frontend không thuộc phạm vi thay đổi |

Current verification: Catalog public-read, admin CRUD, registration filters/cart/batch submission/cancellation, student registration summary, and timetable preview use canonical API/DTOs. Backend: 66 tests pass, 7 MySQL/gateway integration tests are skipped, Ruff passes, and SQLite Alembic upgrade/schema check plus legacy-rate backfill pass. Frontend production build/type-check passes. Compose configuration and OpenAPI paths/schema references are valid; MySQL concurrency and PDF rendering inside Docker remain unverified.
