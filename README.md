# QLDT — Quản lý và đăng ký học phần

Dự án môn IT3180, Nhóm 20. Stack: React + TypeScript, FastAPI, MySQL.
Chức năng hiện có gồm đăng ký học phần, quản trị lớp, thời khóa biểu, điểm danh, bảng điểm
theo lớp và xuất báo cáo Excel cho giảng viên phụ trách.

## Chạy FE–BE–DB local (Windows)

Yêu cầu Docker Desktop, Python 3.12+, Node.js 20+ và npm. Tại thư mục gốc, tạo cấu hình một lần:

```powershell
Copy-Item .env.example .env
```

Thay `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD` và `JWT_SECRET` trong `.env` (JWT tối thiểu 32 ký tự). Chạy MySQL:

```powershell
docker compose up -d db
```

### Nạp database mẫu đầy đủ (mặc định)

Bộ dữ liệu mặc định gồm 1.000 sinh viên, 10 giảng viên, 100 môn và 400 lớp trong học kỳ `2026.1`.
Các lệnh dưới đây tạo lại toàn bộ bảng và nạp dữ liệu mẫu. Nếu database đã có dữ liệu cần giữ,
lệnh `mysqldump` đầu tiên sẽ sao lưu vào `qldt-backup.sql`.

```powershell
docker compose exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --databases qldt > /tmp/qldt-backup.sql'
docker compose cp db:/tmp/qldt-backup.sql qldt-backup.sql
docker compose cp db/schema.sql db:/tmp/schema.sql
docker compose cp db/seed/seed.sql db:/tmp/seed.sql
docker compose exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot < /tmp/schema.sql'
docker compose exec -T db sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot qldt < /tmp/seed.sql'
```

> Dùng `db/schema.sql` + `db/seed/seed.sql` **thay cho** `alembic upgrade head` +
> `python -m scripts.seed`; không chạy cả hai cách trên cùng một database. Dữ liệu nằm trong Docker
> volume `dbdata` nên chỉ cần nạp một lần; nạp lại khi muốn reset hoặc sau `docker compose down -v`.

Mở terminal thứ hai để chạy backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
alembic stamp head   # đánh dấu schema đã khớp migration, không tạo lại bảng
uvicorn app.main:app --reload
```

Mở terminal thứ ba để chạy frontend:

```powershell
cd frontend
npm install
npm run dev
```

Vite chạy tại `http://localhost:5173`, proxy `/api` tới backend `http://localhost:8000`. API docs: `http://localhost:8000/api/docs`; health: `http://localhost:8000/health`.

Bộ dữ liệu đầy đủ tạo tài khoản `admin / admin`, `gv001`–`gv010 / 123456` và
`sv20210001`–`sv20211000 / 123456`. Chỉ dùng các mật khẩu mẫu ở môi trường local.

### Dùng dữ liệu dev tối thiểu (tùy chọn)

Nếu không cần bộ dữ liệu đầy đủ, bỏ qua phần nạp database ở trên và dùng migration + seed dev:

```powershell
cd backend
alembic upgrade head
python -m scripts.seed
```

Seed dev chỉ tạo `admin`, `gv001`, `sv20210001`, 1 môn (`IT3180`) và 1 lớp (`150001`).
Không chạy cách này trên database đã nạp full seed.

## Chạy kiểm tra

```powershell
# backend (trong backend/ và đã activate .venv)
ruff check .
pytest

# frontend (trong frontend/)
npm run build
```

## Kiểm thử quản trị đào tạo (Feature 10)

Sau khi nạp bộ dữ liệu đầy đủ (hoặc dev seed), nạp thêm bộ dữ liệu thử nghiệm:

```powershell
cd backend
python -m scripts.seed_test_data
pytest
pytest -m integration
```

`pytest -m integration` cần MySQL, gateway và frontend đang chạy; xem hướng dẫn đầy đủ,
bảng dữ liệu và checklist giao diện tại [docs/testing/feature10-admin-training.md](docs/testing/feature10-admin-training.md).

## Nguồn dữ liệu và hợp đồng

- `db/schema.sql` và `db/seed/seed.sql` là schema/seed SQL chuẩn; xem [db/README.md](db/README.md). Không nạp SQL seed lên database đã có dữ liệu nếu chưa xác nhận tác động.
- Hợp đồng FE–BE nằm tại `contracts/openapi.yaml` và `contracts/api-types.ts`. JSON dùng camelCase; object môn/lớp/học kỳ trả `id`, còn request tham chiếu dùng `subjectId`, `sectionId`, `semesterId`.
- Backend theo luồng `controller → service → repository → entity`; nghiệp vụ đăng ký, xung đột và sĩ số do server quản lý.
- [backend/README.md](backend/README.md) và [frontend/README.md](frontend/README.md) có ghi chú riêng cho từng ứng dụng.
