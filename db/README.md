# Database Workspace

Database source is organized here:

- `schema.sql`: relational schema.
- `seed/seed.sql`: sample accounts and academic data.
- `../backend/migrations/`: Alembic migrations used by the API and CI; keep them aligned with this canonical SQL schema.

Requires MySQL 8.0.16 or later. These SQL files are the canonical full sample database path.
On a new, empty database, load the schema and then the seed:

```bash
mysql -u root -p < schema.sql
mysql -u root -p < seed/seed.sql
```

For an API-managed database, create the `qldt` database and run `alembic upgrade head`
from `backend/` instead. Do not load `schema.sql` and apply the initial Alembic migration
to the same empty database; they are alternate ways to create the same schema.

For routine local application development, the root [README](../README.md) loads this full
sample data by default, then runs `alembic stamp head` from `backend/` so future migrations know
the schema is current. If you prefer the small idempotent fixture instead, use
`alembic upgrade head` and `python -m scripts.seed`; do not combine that path with the full SQL
seed. Neither seed command is a database reset or a repair command; inspect/back up existing data
before changing or reloading it.

## Sample accounts and data

The seed now has exactly one ADMIN. Its password is `admin`; lecturer and student accounts use `123456`.

| Role | Username | Password | Role-specific ID |
|---|---|---|---|
| ADMIN | `admin` | `admin` | None |
| LECTURER | `gv001` through `gv010` | `123456` | `GV001` through `GV010` |
| STUDENT | `sv20210001` through `sv20211000` | `123456` | `20210001` through `20211000` |

The seed contains 1 admin, 10 lecturers, 1,000 students, 100 subjects, 1 active semester (`2026.1`, `semester_id = 1`), 30 rooms, and 400 sections in this single active registration semester. Registrations start empty and `current_enrollment` starts at 0. Student usernames use `sv` followed by student code.

Do not expose password hashes to the client.

### Dữ liệu mẫu học phí (Module Học phí & Biên lai)
Dữ liệu khởi tạo cho học kỳ 2026.1 bao gồm:
- Đơn giá học phí mẫu: 450.000 ₫/TCHP (chung) và 500.000 ₫/TCHP (khóa K66 ngành CNTT).
- 3 đợt nộp học phí mẫu (tỷ lệ 50%, 30%, 20%).
- Miễn giảm học phí mẫu cho tài khoản `sv20210001` (50%) và `sv20210002` (2.000.000 ₫).
- Một số môn học có số tín chỉ học phí (TCHP) khác tín chỉ học tập (TC).

*LƯU Ý QUAN TRỌNG: Mọi số liệu về đơn giá, tỷ lệ miễn giảm, hạn nộp học phí trong seed đều là **dữ liệu giả định (mock data)** nhằm mục đích kiểm thử và minh họa hệ thống, hoàn toàn không phải số liệu chính thức của nhà trường.*

Đơn giá có `effective_from`/`effective_to`; khi tạo hóa đơn, backend chọn đơn giá phù hợp theo thời điểm bắt đầu học kỳ và mức đặc hiệu khóa/ngành. Thay đổi schema cần chạy Alembic migration `79e0a29b3c41` và `4a81f9032d76` (hoặc nạp lại schema SQL chuẩn cho database mẫu); không áp dụng migration lên database vừa tạo bằng `schema.sql` rồi đã `stamp head`.
