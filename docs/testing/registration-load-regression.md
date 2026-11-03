# Kiểm thử hiệu năng cổng đăng ký và hồi quy UC005/UC006

## 1. Phạm vi

Bộ kiểm thử này bổ sung hai lớp kiểm tra cho cổng đăng ký học phần:

- **Regression API test** (`backend/tests/test_registration_portal_regression.py`): xác minh dữ liệu danh mục mà sinh viên nhìn thấy trước đăng ký, sau đăng ký và sau hủy; response đăng ký; chặn đăng ký trùng; danh sách đăng ký cá nhân; và RBAC.
- **Gateway load test** (`tests/performance/registration-load.js`): dùng k6 gửi tải qua gateway vào luồng đọc danh mục và đăng ký của tôi. Chế độ mặc định chỉ đọc. Chế độ `cycle` mới ghi dữ liệu; nó đăng ký, xác minh, rồi hủy đúng `registration ID` vừa tạo.

Các bài test hiện có trong `backend/tests/test_concurrency_and_security.py` tiếp tục đảm nhiệm race-condition ở tầng service (10 sinh viên tranh một chỗ). Bài test mới không thay thế bài đó và không thay đổi business logic.

Phạm vi hiệu năng là HTTP API qua gateway, không đo thời gian render React trong trình duyệt. NFR-005 trong `docs/specs/srs/99-nfr.md` đặt mục tiêu phản hồi dưới 2 giây; trong bộ test này mục tiêu được cụ thể hóa thành p95 dưới 2.000 ms cho các endpoint được đo.

## 2. Hồi quy nhanh (SQLite, không cần MySQL)

Trên Debian 13, từ thư mục gốc repository:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt

ruff check .
pytest -q tests/test_registration_portal_regression.py
pytest -q tests/test_registration.py tests/test_change_section.py tests/test_concurrency_and_security.py
pytest -q
```

`pytest` mặc định sử dụng SQLite trong bộ nhớ. Không cần cấu hình MySQL để chạy các regression test này.

## 3. Khởi động hệ thống để đo tải

Chỉ chạy load/stress test trên local hoặc staging được phép kiểm thử. **Không chạy chế độ ghi trên production hoặc database dùng chung.** Không sử dụng tài khoản sinh viên thật.

Cách dựng gateway/backend/DB theo hướng dẫn chính của repository:

```bash
# Từ thư mục gốc; chỉ tạo .env cho môi trường local
cp .env.example .env
# Sửa MYSQL_PASSWORD, MYSQL_ROOT_PASSWORD và JWT_SECRET trong .env trước khi chạy.

docker compose up -d --build db
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python -m scripts.seed
docker compose up -d --build backend gateway

curl --fail http://127.0.0.1:8080/health
curl --fail http://127.0.0.1:8080/health/backend
```

Bộ seed đầy đủ trong `db/seed/seed.sql` có tài khoản local `sv20210001` đến `sv20211000` (mật khẩu mẫu `123456`) và 400 lớp học phần. Dùng chúng chỉ trên database local dùng riêng để kiểm thử. Có thể lấy `SEMESTER_ID` từ `GET /api/semesters/current` hoặc `GET /api/semesters` sau khi đăng nhập.

## 4. Cài và chạy k6 trên Debian 13

Cách ít phụ thuộc nhất là dùng image chính thức của k6 qua Docker:

```bash
Kiểm tra Docker Engine và Compose plugin đã cài theo cách triển khai Docker trên Debian của máy bạn:

```bash
docker version
docker compose version
```

Nếu user hiện tại chưa có quyền Docker, chạy các lệnh `docker` bằng `sudo` (không cần thêm user vào nhóm `docker`). Từ thư mục gốc repo, nạp cấu hình kiểm thử:

```bash
export BASE_URL=http://127.0.0.1:8080
export SEMESTER_ID=1                 # thay bằng ID học kỳ thực tế từ API
export STUDENT_USERNAME=sv20210001
read -rsp 'Student password: ' STUDENT_PASSWORD
printf '\n'
export STUDENT_PASSWORD
```

Smoke test trước, sau đó chạy load/stress/soak:

```bash
docker run --rm --network host \
  -e BASE_URL -e SEMESTER_ID -e STUDENT_USERNAME -e STUDENT_PASSWORD \
  -e PROFILE=smoke -e MODE=read \
  -v "$PWD:/work:ro" grafana/k6:latest run /work/tests/performance/registration-load.js

# Load: ramp 10 -> 25 VUs, giữ 25 VUs, rồi giảm tải
docker run --rm --network host \
  -e BASE_URL -e SEMESTER_ID -e STUDENT_USERNAME -e STUDENT_PASSWORD \
  -e PROFILE=load -e MODE=read \
  -v "$PWD:/work:ro" grafana/k6:latest run /work/tests/performance/registration-load.js

# Stress: ramp tối đa 100 VUs; chỉ dùng trên local/staging đã được cấp phép
docker run --rm --network host \
  -e BASE_URL -e SEMESTER_ID -e STUDENT_USERNAME -e STUDENT_PASSWORD \
  -e PROFILE=stress -e MODE=read \
  -v "$PWD:/work:ro" grafana/k6:latest run /work/tests/performance/registration-load.js

# Soak: giữ 20 VUs trong 10 phút
docker run --rm --network host \
  -e BASE_URL -e SEMESTER_ID -e STUDENT_USERNAME -e STUDENT_PASSWORD \
  -e PROFILE=soak -e MODE=read \
  -v "$PWD:/work:ro" grafana/k6:latest run /work/tests/performance/registration-load.js
```

`MODE=read` là mặc định an toàn: mỗi VU đăng nhập một lần, sau đó gọi danh mục lớp và danh sách đăng ký của sinh viên. Có thể dùng chung một tài khoản test ở chế độ chỉ đọc. Mặc định mỗi iteration nghỉ 2 giây ở read mode; cycle mode nghỉ 6 giây để 25 VU có tải xấp xỉ 25 request/giây theo luồng tuần tự. Có thể chỉnh bằng `THINK_TIME_SECONDS`.

## 5. Load test có ghi dữ liệu (opt-in)

Chế độ `MODE=cycle` kiểm thử luồng ghi thật: kiểm tra sinh viên chưa sở hữu lớp đích, POST đăng ký, GET xác minh registration xuất hiện, DELETE đúng registration ID vừa tạo, rồi GET xác minh bản ghi đã biến mất.

Chỉ chạy khi đã chuẩn bị **database local/staging riêng**, một lớp kiểm thử còn đủ chỗ cho số VU tối đa, và dải tài khoản test riêng biệt. Mỗi VU cần một tài khoản sinh viên khác nhau; tài khoản không được có đăng ký môn trùng, lịch trùng hoặc vượt giới hạn tín chỉ. Không dùng tài khoản admin, giảng viên hoặc sinh viên thật.

Ví dụ dưới đây chạy 25 VU tối đa (`PROFILE=load`). Dải `sv20210001`…`sv20210025` phải là tài khoản test riêng, và lớp `SECTION_ID` phải còn ít nhất 25 chỗ trống. Hãy kiểm tra các điều kiện này trước khi chạy:

```bash
export STUDENT_USERNAME_PREFIX=sv2021
export STUDENT_START_NUMBER=1
export STUDENT_NUMBER_WIDTH=4
export SECTION_ID=123                # thay bằng ID lớp thử nghiệm thực tế

# Cờ xác nhận bắt buộc; không được bật trên production.
export ALLOW_REGISTRATION_WRITES=true

docker run --rm --network host \
  -e BASE_URL -e SEMESTER_ID -e STUDENT_PASSWORD \
  -e STUDENT_USERNAME_PREFIX -e STUDENT_START_NUMBER -e STUDENT_NUMBER_WIDTH \
  -e SECTION_ID -e ALLOW_REGISTRATION_WRITES \
  -e PROFILE=load -e MODE=cycle \
  -v "$PWD:/work:ro" grafana/k6:latest run /work/tests/performance/registration-load.js
```

Trong `cycle`, nếu tài khoản đã đăng ký lớp đích thì iteration đó bị đánh dấu thất bại và **không xóa** đăng ký có sẵn. Script chỉ gửi DELETE với ID trả về từ POST thành công của chính VU hiện tại. Tuy vậy, hãy dùng dữ liệu kiểm thử disposable và kiểm tra database sau bài test; lỗi tiến trình/mạng ở giữa chu kỳ vẫn có thể để lại đăng ký cần dọn thủ công.

PROFILE stress mặc định ramp đến 100 VU; không dùng stress profile với `cycle` trừ khi có tối thiểu 100 tài khoản và 100 chỗ trống phù hợp. Gateway mặc định giới hạn API ở 30 request/giây theo cấu hình Nginx. Stress profile có thể vượt mức này và tạo 429; đây là hành vi rate-limit cần ghi nhận, không phải lý do để chạy lại trên production. Nếu mục tiêu là đo thông lượng backend cao hơn ngưỡng gateway, hãy cấu hình gateway trong staging có kiểm soát và ghi lại cấu hình đó trong báo cáo. Không bỏ qua/che giấu 429: đó là kết quả hữu ích khi đánh giá bảo vệ quá tải.

## 6. Ngưỡng đánh giá và báo cáo

Bộ k6 khai báo các threshold mặc định:

| Metric | Điều kiện đạt |
|---|---:|
| HTTP request failure rate | `< 1%` |
| HTTP request duration | p95 `< 2.000 ms` |
| `GET /api/sections` | p95 `< 2.000 ms` |
| `GET /api/registrations/me` | p95 `< 2.000 ms` |
| Registration lifecycle checks | `> 99%` |
| `POST /api/registrations` (cycle mode) | p95 `< 2.000 ms` |

Sau mỗi lần chạy, lưu stdout của k6 cùng commit SHA, profile, URL môi trường (không lưu token/mật khẩu), loại DB, cấu hình gateway, thời điểm chạy, số VU và kết quả threshold. Có thể thêm `--summary-export=registration-load-summary.json` vào lệnh `k6 run` để lưu summary JSON; lưu artifact ở nơi nội bộ phù hợp và không commit dữ liệu có thông tin đăng nhập.

Khi stress test chạm giới hạn rate-limit, connection pool, DB hoặc tài nguyên máy, ghi rõ điểm bắt đầu xuất hiện 429/5xx và p95/p99 thay vì chỉ báo pass/fail. Không suy luận khả năng chịu tải production từ một lần chạy local.

## 7. Kết hợp với regression hiện có

Từ `backend/`:

```bash
pytest -q tests/test_registration_portal_regression.py
pytest -q tests/test_registration.py tests/test_change_section.py tests/test_concurrency_and_security.py
pytest -q
ruff check .
```

Bài race-condition 10 sinh viên tranh một chỗ hiện hữu vẫn là kiểm thử bất biến sĩ số ở tầng service/SQLite. Chế độ k6 `cycle` đo HTTP end-to-end qua gateway; cần xác nhận concurrency/locking trên MySQL 8.4 của staging trước khi kết luận về triển khai MySQL thực tế.
