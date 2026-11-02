# 01. Tổng quan

## Mục tiêu

QLDT là đồ án IT3180 của Nhóm 20, Trường CNTT&TT, Đại học Bách khoa Hà Nội. Hệ thống quản lý môn học và lớp học phần; sinh viên đăng ký học trực tuyến; sinh viên và giảng viên tra cứu thời khóa biểu/lịch dạy. Hệ thống thay quy trình thủ công dễ trùng phòng, trùng lịch và vượt sĩ số.

## Kiến trúc

- Client-server ba tầng: trình duyệt responsive, REST API trả JSON, cơ sở dữ liệu quan hệ.
- Backend theo MVC phân tầng `View -> Controller -> Service -> Repository -> Entity`.
- Module backend: `auth`, `catalog`, `registration`, `timetable`; package dùng chung `security`.
- CSDL có 11 bảng, gồm các bảng tài khoản, danh mục/lớp học phần, đăng ký, điểm danh và điểm thành phần; lược đồ chuẩn tại `db/schema.sql`.

## Bảo mật và tích hợp

- RBAC với các role `ADMIN`, `LECTURER`, `STUDENT`; tài khoản được nạp sẵn, không có đăng ký tài khoản.
- Mật khẩu Bcrypt; API không trả `password_hash`.
- JWT chứa `userId`, `role`, sống 3600 giây, không có refresh token. Client gửi `Authorization: Bearer <token>` qua HTTPS.
- Security filter kiểm tra role theo endpoint; service kiểm tra quyền sở hữu dữ liệu.
- API conventions FE-BE mới hơn và được ưu tiên khi khác tài liệu thiết kế. `contracts/openapi.yaml` là nguồn hợp đồng cuối khi có.