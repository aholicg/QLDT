-- =====================================================================
-- QLDT - Hệ thống Quản lý & Đăng ký Học phần Trực tuyến
-- Lược đồ quan hệ (16 bảng)
-- Sinh theo: Tài liệu thiết kế phần mềm v1.0 - mục 3.2 và 3.3
--           Quy ước API và JSON (FE-BE) v1.0 - mục 3.2 (đối chiếu tên cột)
-- Mã nguồn chuẩn máy đọc được: openapi.yaml
-- Hệ quản trị: MySQL 8.0 (bắt buộc 8.0.16+ để dùng được CHECK tham chiếu cột khác)
-- Tên bảng / cột: UPPER_SNAKE_CASE; khóa chính *_id, khóa ngoại giữ nguyên hậu tố _id.
-- Toàn bộ khóa ngoại dùng ON DELETE RESTRICT (mục 3.3).
-- =====================================================================

CREATE DATABASE IF NOT EXISTS qldt
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE qldt;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- Dọn dẹp bảng cũ nếu có
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS RECEIPTS;
DROP TABLE IF EXISTS TUITION_PAYMENTS;
DROP TABLE IF EXISTS TUITION_INVOICE_ITEMS;
DROP TABLE IF EXISTS TUITION_INVOICES;
DROP TABLE IF EXISTS TUITION_INSTALLMENTS;
DROP TABLE IF EXISTS TUITION_DISCOUNTS;
DROP TABLE IF EXISTS TUITION_RATES;
DROP TABLE IF EXISTS RECEIPT_SEQUENCES;
DROP TABLE IF EXISTS REGISTRATIONS;
DROP TABLE IF EXISTS COURSE_SECTIONS;
DROP TABLE IF EXISTS LECTURERS;
DROP TABLE IF EXISTS STUDENTS;
DROP TABLE IF EXISTS USERS;
DROP TABLE IF EXISTS SUBJECTS;
DROP TABLE IF EXISTS SEMESTERS;
DROP TABLE IF EXISTS ROOMS;

-- ---------------------------------------------------------------------
-- USERS: tài khoản đăng nhập của mọi vai trò (ADMIN, LECTURER, STUDENT)
-- ---------------------------------------------------------------------
CREATE TABLE USERS (
    user_id       BIGINT       NOT NULL AUTO_INCREMENT COMMENT 'Mã tài khoản',
    username      VARCHAR(50)  NOT NULL                COMMENT 'Tên đăng nhập',
    password_hash VARCHAR(100) NOT NULL                COMMENT 'Mật khẩu đã băm (Bcrypt)',
    full_name     VARCHAR(100) NOT NULL                COMMENT 'Họ và tên',
    email         VARCHAR(100)     NULL                COMMENT 'Email liên hệ',
    role          ENUM('ADMIN', 'LECTURER', 'STUDENT') NOT NULL COMMENT 'Vai trò',
    status        ENUM('ACTIVE', 'LOCKED') NOT NULL DEFAULT 'ACTIVE' COMMENT 'Trạng thái tài khoản',
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_users_username (username),
    UNIQUE KEY uk_users_email (email)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Tài khoản đăng nhập của mọi vai trò';

-- ---------------------------------------------------------------------
-- STUDENTS: hồ sơ sinh viên, liên kết 1-1 với USERS
-- ---------------------------------------------------------------------
CREATE TABLE STUDENTS (
    student_id   BIGINT      NOT NULL AUTO_INCREMENT COMMENT 'Mã sinh viên (khóa kỹ thuật)',
    user_id      BIGINT      NOT NULL                COMMENT 'Tài khoản tương ứng',
    student_code VARCHAR(20) NOT NULL                COMMENT 'Mã số sinh viên',
    cohort       VARCHAR(10)     NULL                COMMENT 'Khóa',
    major        VARCHAR(100)    NULL                COMMENT 'Ngành',
    PRIMARY KEY (student_id),
    UNIQUE KEY uk_students_user_id (user_id),
    UNIQUE KEY uk_students_code (student_code),
    CONSTRAINT fk_students_user FOREIGN KEY (user_id) REFERENCES USERS (user_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Hồ sơ sinh viên';

-- ---------------------------------------------------------------------
-- LECTURERS: hồ sơ giảng viên, liên kết 1-1 với USERS
-- ---------------------------------------------------------------------
CREATE TABLE LECTURERS (
    lecturer_id   BIGINT      NOT NULL AUTO_INCREMENT COMMENT 'Mã giảng viên (khóa kỹ thuật)',
    user_id       BIGINT      NOT NULL                COMMENT 'Tài khoản tương ứng',
    lecturer_code VARCHAR(20) NOT NULL                COMMENT 'Mã giảng viên',
    department    VARCHAR(100)    NULL                COMMENT 'Bộ môn / khoa',
    PRIMARY KEY (lecturer_id),
    UNIQUE KEY uk_lecturers_user_id (user_id),
    UNIQUE KEY uk_lecturers_code (lecturer_code),
    CONSTRAINT fk_lecturers_user FOREIGN KEY (user_id) REFERENCES USERS (user_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Hồ sơ giảng viên';

-- ---------------------------------------------------------------------
-- SUBJECTS: danh mục môn học
-- ---------------------------------------------------------------------
CREATE TABLE SUBJECTS (
    subject_id      BIGINT         NOT NULL AUTO_INCREMENT COMMENT 'Mã môn học (khóa kỹ thuật)',
    subject_code    VARCHAR(20)    NOT NULL                COMMENT 'Mã môn học',
    name            VARCHAR(150)   NOT NULL                COMMENT 'Tên môn học',
    credits         INT            NOT NULL                COMMENT 'Số tín chỉ học tập',
    tuition_credits DECIMAL(4, 1)      NULL                COMMENT 'Số tín chỉ học phí (TCHP)',
    description     TEXT               NULL                COMMENT 'Mô tả',
    PRIMARY KEY (subject_id),
    UNIQUE KEY uk_subjects_code (subject_code),
    CONSTRAINT ck_subjects_credits CHECK (credits > 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Danh mục môn học';

-- ---------------------------------------------------------------------
-- SEMESTERS: học kỳ. start_date là mốc tính tuần 1 (thứ hai đầu học kỳ).
-- ---------------------------------------------------------------------
CREATE TABLE SEMESTERS (
    semester_id   BIGINT      NOT NULL AUTO_INCREMENT COMMENT 'Mã học kỳ',
    semester_code VARCHAR(10) NOT NULL                COMMENT 'Mã học kỳ, ví dụ 2026.1',
    name          VARCHAR(50) NOT NULL                COMMENT 'Tên học kỳ',
    start_date    DATE        NOT NULL                COMMENT 'Ngày bắt đầu (mốc tính tuần 1)',
    end_date      DATE        NOT NULL                COMMENT 'Ngày kết thúc',
    num_weeks     INT         NOT NULL                COMMENT 'Số tuần học',
    PRIMARY KEY (semester_id),
    UNIQUE KEY uk_semesters_code (semester_code),
    CONSTRAINT ck_semesters_dates CHECK (end_date > start_date),
    CONSTRAINT ck_semesters_weeks CHECK (num_weeks > 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Học kỳ';

-- ---------------------------------------------------------------------
-- ROOMS: phòng học
-- ---------------------------------------------------------------------
CREATE TABLE ROOMS (
    room_id   BIGINT      NOT NULL AUTO_INCREMENT COMMENT 'Mã phòng',
    room_code VARCHAR(20) NOT NULL                COMMENT 'Mã phòng, ví dụ D9-301',
    building  VARCHAR(50)     NULL                COMMENT 'Tòa nhà',
    capacity  INT         NOT NULL                COMMENT 'Sức chứa',
    PRIMARY KEY (room_id),
    UNIQUE KEY uk_rooms_code (room_code),
    CONSTRAINT ck_rooms_capacity CHECK (capacity > 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Phòng học';

-- ---------------------------------------------------------------------
-- COURSE_SECTIONS: bảng trung tâm, liên kết SUBJECTS, SEMESTERS,
-- ROOMS và LECTURERS. current_enrollment là sĩ số hiện tại.
-- ---------------------------------------------------------------------
CREATE TABLE COURSE_SECTIONS (
    section_id         BIGINT      NOT NULL AUTO_INCREMENT COMMENT 'Mã lớp học phần (khóa kỹ thuật)',
    section_code       VARCHAR(20) NOT NULL                COMMENT 'Mã lớp học phần',
    subject_id         BIGINT      NOT NULL                COMMENT 'Môn học',
    semester_id        BIGINT      NOT NULL                COMMENT 'Học kỳ',
    lecturer_id        BIGINT      NOT NULL                COMMENT 'Giảng viên phụ trách',
    room_id            BIGINT      NOT NULL                COMMENT 'Phòng học',
    day_of_week        TINYINT     NOT NULL                COMMENT 'Thứ (2 = Thứ hai .. 8 = Chủ nhật)',
    start_period       TINYINT     NOT NULL                COMMENT 'Tiết bắt đầu',
    end_period         TINYINT     NOT NULL                COMMENT 'Tiết kết thúc',
    start_week         TINYINT     NOT NULL                COMMENT 'Tuần bắt đầu',
    end_week           TINYINT     NOT NULL                COMMENT 'Tuần kết thúc',
    max_capacity       INT         NOT NULL                COMMENT 'Sĩ số tối đa',
    current_enrollment INT         NOT NULL DEFAULT 0      COMMENT 'Sĩ số hiện tại',
    PRIMARY KEY (section_id),
    UNIQUE KEY uk_course_sections_code (section_code),
    KEY idx_course_sections_semester_subject (semester_id, subject_id),
    KEY idx_course_sections_lecturer_semester (lecturer_id, semester_id),
    CONSTRAINT fk_course_sections_subject FOREIGN KEY (subject_id) REFERENCES SUBJECTS (subject_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_course_sections_semester FOREIGN KEY (semester_id) REFERENCES SEMESTERS (semester_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_course_sections_lecturer FOREIGN KEY (lecturer_id) REFERENCES LECTURERS (lecturer_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_course_sections_room FOREIGN KEY (room_id) REFERENCES ROOMS (room_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_course_sections_day CHECK (day_of_week BETWEEN 2 AND 8),
    CONSTRAINT ck_course_sections_start_period CHECK (start_period BETWEEN 1 AND 12),
    CONSTRAINT ck_course_sections_end_period CHECK (end_period >= start_period AND end_period <= 12),
    CONSTRAINT ck_course_sections_start_week CHECK (start_week >= 1),
    CONSTRAINT ck_course_sections_end_week CHECK (end_week >= start_week),
    CONSTRAINT ck_course_sections_max_capacity CHECK (max_capacity > 0),
    CONSTRAINT ck_course_sections_enrollment CHECK (current_enrollment >= 0 AND current_enrollment <= max_capacity)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Lớp học phần được mở trong học kỳ';

-- ---------------------------------------------------------------------
-- REGISTRATIONS: bảng liên kết nhiều-nhiều giữa STUDENTS và
-- COURSE_SECTIONS.
-- ---------------------------------------------------------------------
CREATE TABLE REGISTRATIONS (
    registration_id BIGINT   NOT NULL AUTO_INCREMENT COMMENT 'Mã đăng ký',
    student_id      BIGINT   NOT NULL                COMMENT 'Sinh viên',
    section_id      BIGINT   NOT NULL                COMMENT 'Lớp học phần',
    registered_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm đăng ký',
    PRIMARY KEY (registration_id),
    UNIQUE KEY uk_registrations_student_section (student_id, section_id),
    KEY idx_registrations_section (section_id),
    KEY idx_registrations_student (student_id),
    CONSTRAINT fk_registrations_student FOREIGN KEY (student_id) REFERENCES STUDENTS (student_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_registrations_section FOREIGN KEY (section_id) REFERENCES COURSE_SECTIONS (section_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Bản ghi đăng ký lớp học phần của sinh viên';

-- ---------------------------------------------------------------------
-- ATTENDANCE_RECORDS: điểm danh từng sinh viên theo ngày học
-- ---------------------------------------------------------------------
CREATE TABLE ATTENDANCE_RECORDS (
    attendance_id   BIGINT NOT NULL AUTO_INCREMENT,
    section_id      BIGINT NOT NULL,
    student_id      BIGINT NOT NULL,
    class_date      DATE NOT NULL,
    status          ENUM('PRESENT', 'ABSENT', 'LATE', 'EXCUSED') NOT NULL,
    marked_by_user_id BIGINT NOT NULL,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (attendance_id),
    UNIQUE KEY uq_attendance_section_student_date (section_id, student_id, class_date),
    KEY ix_attendance_section_date (section_id, class_date),
    CONSTRAINT fk_attendance_section FOREIGN KEY (section_id) REFERENCES COURSE_SECTIONS (section_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_attendance_student FOREIGN KEY (student_id) REFERENCES STUDENTS (student_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_attendance_marked_by FOREIGN KEY (marked_by_user_id) REFERENCES USERS (user_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Điểm danh theo buổi học phần';

-- ---------------------------------------------------------------------
-- SECTION_GRADE_COMPONENTS: cấu hình cột điểm theo từng lớp/học kỳ
-- ---------------------------------------------------------------------
CREATE TABLE SECTION_GRADE_COMPONENTS (
    component_id      BIGINT NOT NULL AUTO_INCREMENT,
    section_id        BIGINT NOT NULL,
    name              VARCHAR(80) NOT NULL,
    weight_percentage DECIMAL(5,2) NOT NULL,
    max_score         DECIMAL(5,2) NOT NULL,
    sort_order        INT NOT NULL,
    PRIMARY KEY (component_id),
    UNIQUE KEY uq_grade_components_section_name (section_id, name),
    UNIQUE KEY uq_grade_components_section_order (section_id, sort_order),
    KEY ix_grade_components_section (section_id),
    CONSTRAINT fk_grade_components_section FOREIGN KEY (section_id) REFERENCES COURSE_SECTIONS (section_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_grade_components_weight_range CHECK (weight_percentage > 0 AND weight_percentage <= 100),
    CONSTRAINT ck_grade_components_max_score_positive CHECK (max_score > 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Cấu hình cột điểm của lớp học phần';

-- ---------------------------------------------------------------------
-- STUDENT_GRADES: điểm từng sinh viên ở từng cột điểm
-- ---------------------------------------------------------------------
CREATE TABLE STUDENT_GRADES (
    grade_id          BIGINT NOT NULL AUTO_INCREMENT,
    component_id      BIGINT NOT NULL,
    student_id        BIGINT NOT NULL,
    score             DECIMAL(5,2) NOT NULL,
    updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_by_user_id BIGINT NOT NULL,
    PRIMARY KEY (grade_id),
    UNIQUE KEY uq_student_grades_component_student (component_id, student_id),
    KEY ix_student_grades_student (student_id),
    CONSTRAINT fk_student_grades_component FOREIGN KEY (component_id) REFERENCES SECTION_GRADE_COMPONENTS (component_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_student_grades_student FOREIGN KEY (student_id) REFERENCES STUDENTS (student_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_student_grades_updated_by FOREIGN KEY (updated_by_user_id) REFERENCES USERS (user_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_student_grades_score_nonnegative CHECK (score >= 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Điểm thành phần của sinh viên';
-- TUITION_RATES: đơn giá một tín chỉ học phí theo học kỳ / khóa / ngành
-- ---------------------------------------------------------------------
CREATE TABLE TUITION_RATES (
    rate_id          BIGINT       NOT NULL AUTO_INCREMENT COMMENT 'Mã đơn giá',
    semester_id      BIGINT       NOT NULL                COMMENT 'Học kỳ áp dụng',
    cohort           VARCHAR(10)      NULL                COMMENT 'Khóa sinh viên (NULL = áp dụng chung)',
    major            VARCHAR(100)     NULL                COMMENT 'Ngành học (NULL = áp dụng chung)',
    effective_from   DATE         NOT NULL                COMMENT 'Ngày bắt đầu hiệu lực',
    effective_to     DATE             NULL                COMMENT 'Ngày kết thúc hiệu lực, NULL = không giới hạn',
    price_per_credit BIGINT       NOT NULL                COMMENT 'Đơn giá 1 TCHP (VND)',
    description      VARCHAR(255)     NULL                COMMENT 'Mô tả / ghi chú',
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm tạo',
    PRIMARY KEY (rate_id),
    KEY idx_tuition_rates_lookup (semester_id, cohort, major),
    KEY idx_tuition_rates_effective_lookup (semester_id, cohort, major, effective_from, effective_to),
    CONSTRAINT fk_tuition_rates_semester FOREIGN KEY (semester_id) REFERENCES SEMESTERS (semester_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_tuition_rates_price CHECK (price_per_credit > 0),
    CONSTRAINT ck_tuition_rates_effective_range CHECK (effective_to IS NULL OR effective_to >= effective_from)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Đơn giá học phí theo tín chỉ học phí';

-- ---------------------------------------------------------------------
-- TUITION_DISCOUNTS: các khoản miễn giảm học phí cho sinh viên
-- ---------------------------------------------------------------------
CREATE TABLE TUITION_DISCOUNTS (
    discount_id      BIGINT        NOT NULL AUTO_INCREMENT COMMENT 'Mã miễn giảm',
    student_id       BIGINT        NOT NULL                COMMENT 'Sinh viên được miễn giảm',
    semester_id      BIGINT        NOT NULL                COMMENT 'Học kỳ áp dụng',
    discount_percent DECIMAL(5, 2) NOT NULL DEFAULT 0.00   COMMENT 'Phần trăm miễn giảm (0-100)',
    fixed_amount     BIGINT        NOT NULL DEFAULT 0      COMMENT 'Số tiền miễn giảm cố định (VND)',
    reason           VARCHAR(255)  NOT NULL                COMMENT 'Lý do miễn giảm',
    granted_by       VARCHAR(100)  NOT NULL                COMMENT 'Người cấp / quyết định',
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm tạo',
    PRIMARY KEY (discount_id),
    KEY idx_tuition_discounts_student_semester (student_id, semester_id),
    CONSTRAINT fk_tuition_discounts_student FOREIGN KEY (student_id) REFERENCES STUDENTS (student_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_tuition_discounts_semester FOREIGN KEY (semester_id) REFERENCES SEMESTERS (semester_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_tuition_discounts_percent CHECK (discount_percent >= 0 AND discount_percent <= 100),
    CONSTRAINT ck_tuition_discounts_fixed CHECK (fixed_amount >= 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Miễn giảm học phí';

-- ---------------------------------------------------------------------
-- TUITION_INSTALLMENTS: cấu hình các đợt nộp học phí trong học kỳ
-- ---------------------------------------------------------------------
CREATE TABLE TUITION_INSTALLMENTS (
    installment_id    BIGINT        NOT NULL AUTO_INCREMENT COMMENT 'Mã đợt nộp',
    semester_id       BIGINT        NOT NULL                COMMENT 'Học kỳ áp dụng',
    installment_order INT           NOT NULL                COMMENT 'Thứ tự đợt (1, 2, ...)',
    name              VARCHAR(100)  NOT NULL                COMMENT 'Tên đợt nộp',
    due_date          DATE          NOT NULL                COMMENT 'Hạn nộp',
    percentage        DECIMAL(5, 2)     NULL                COMMENT 'Tỷ lệ % nộp',
    fixed_amount      BIGINT            NULL                COMMENT 'Số tiền nộp cố định (VND)',
    PRIMARY KEY (installment_id),
    UNIQUE KEY uk_installments_semester_order (semester_id, installment_order),
    CONSTRAINT fk_tuition_installments_semester FOREIGN KEY (semester_id) REFERENCES SEMESTERS (semester_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_tuition_installments_order CHECK (installment_order > 0),
    CONSTRAINT ck_tuition_installments_amount_basis CHECK (
        (percentage IS NOT NULL AND fixed_amount IS NULL) OR
        (percentage IS NULL AND fixed_amount IS NOT NULL)
    ),
    CONSTRAINT ck_tuition_installments_percentage CHECK (
        percentage IS NULL OR (percentage >= 0 AND percentage <= 100)
    ),
    CONSTRAINT ck_tuition_installments_fixed CHECK (fixed_amount IS NULL OR fixed_amount >= 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Cấu hình đợt nộp học phí';

-- ---------------------------------------------------------------------
-- TUITION_INVOICES: hóa đơn học phí của sinh viên theo học kỳ (1 dòng/sv/kỳ)
-- ---------------------------------------------------------------------
CREATE TABLE TUITION_INVOICES (
    invoice_id     BIGINT                                                  NOT NULL AUTO_INCREMENT COMMENT 'Mã hóa đơn',
    student_id     BIGINT                                                  NOT NULL                COMMENT 'Sinh viên',
    semester_id    BIGINT                                                  NOT NULL                COMMENT 'Học kỳ',
    total_tuition  BIGINT                                                  NOT NULL DEFAULT 0      COMMENT 'Tổng học phí môn học (VND)',
    total_discount BIGINT                                                  NOT NULL DEFAULT 0      COMMENT 'Tổng miễn giảm (VND)',
    amount_due     BIGINT                                                  NOT NULL DEFAULT 0      COMMENT 'Số tiền phải nộp (VND)',
    amount_paid    BIGINT                                                  NOT NULL DEFAULT 0      COMMENT 'Số tiền đã nộp lũy kế (VND)',
    status         ENUM('UNPAID', 'PARTIALLY_PAID', 'PAID', 'CANCELLED')    NOT NULL DEFAULT 'UNPAID' COMMENT 'Trạng thái hóa đơn',
    is_stale       BOOLEAN                                                 NOT NULL DEFAULT FALSE  COMMENT 'Đánh dấu thay đổi môn sau khi tính',
    created_at     DATETIME                                                NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm tạo',
    updated_at     DATETIME                                                NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Cập nhật cuối',
    PRIMARY KEY (invoice_id),
    UNIQUE KEY uk_tuition_invoices_student_semester (student_id, semester_id),
    CONSTRAINT fk_tuition_invoices_student FOREIGN KEY (student_id) REFERENCES STUDENTS (student_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_tuition_invoices_semester FOREIGN KEY (semester_id) REFERENCES SEMESTERS (semester_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_tuition_invoices_total CHECK (total_tuition >= 0),
    CONSTRAINT ck_tuition_invoices_discount CHECK (total_discount >= 0),
    CONSTRAINT ck_tuition_invoices_due CHECK (amount_due >= 0),
    CONSTRAINT ck_tuition_invoices_paid CHECK (amount_paid >= 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Hóa đơn học phí';

-- ---------------------------------------------------------------------
-- TUITION_INVOICE_ITEMS: snapshot chi tiết các môn học tại thời điểm tính
-- ---------------------------------------------------------------------
CREATE TABLE TUITION_INVOICE_ITEMS (
    item_id          BIGINT        NOT NULL AUTO_INCREMENT COMMENT 'Mã dòng hóa đơn',
    invoice_id       BIGINT        NOT NULL                COMMENT 'Hóa đơn',
    subject_id       BIGINT        NOT NULL                COMMENT 'Môn học',
    subject_code     VARCHAR(20)   NOT NULL                COMMENT 'Mã môn học (snapshot)',
    subject_name     VARCHAR(150)  NOT NULL                COMMENT 'Tên môn học (snapshot)',
    credits          INT           NOT NULL                COMMENT 'Số TC (snapshot)',
    tuition_credits  DECIMAL(4, 1) NOT NULL                COMMENT 'Số TCHP (snapshot)',
    price_per_credit BIGINT        NOT NULL                COMMENT 'Đơn giá 1 TCHP (snapshot)',
    amount           BIGINT        NOT NULL                COMMENT 'Thành tiền môn học (VND)',
    PRIMARY KEY (item_id),
    KEY idx_tuition_invoice_items_invoice (invoice_id),
    CONSTRAINT fk_invoice_items_invoice FOREIGN KEY (invoice_id) REFERENCES TUITION_INVOICES (invoice_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_invoice_items_subject FOREIGN KEY (subject_id) REFERENCES SUBJECTS (subject_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_invoice_items_credits CHECK (credits > 0),
    CONSTRAINT ck_invoice_items_tuition_credits CHECK (tuition_credits > 0),
    CONSTRAINT ck_invoice_items_price CHECK (price_per_credit > 0),
    CONSTRAINT ck_invoice_items_amount CHECK (amount >= 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Dòng chi tiết môn học trong hóa đơn học phí';

-- ---------------------------------------------------------------------
-- TUITION_PAYMENTS: lịch sử các lần thanh toán học phí
-- ---------------------------------------------------------------------
CREATE TABLE TUITION_PAYMENTS (
    payment_id      BIGINT      NOT NULL AUTO_INCREMENT COMMENT 'Mã giao dịch nộp tiền',
    invoice_id      BIGINT      NOT NULL                COMMENT 'Hóa đơn',
    student_id      BIGINT      NOT NULL                COMMENT 'Sinh viên nộp',
    installment_id  BIGINT          NULL                COMMENT 'Đợt nộp tương ứng (nếu có)',
    amount          BIGINT      NOT NULL                COMMENT 'Số tiền nộp lần này (VND)',
    idempotency_key VARCHAR(64) NOT NULL                COMMENT 'Khóa chống trùng lặp từ client',
    payment_method  VARCHAR(50) NOT NULL DEFAULT 'SIMULATED' COMMENT 'Phương thức thanh toán',
    paid_at         DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm thanh toán',
    PRIMARY KEY (payment_id),
    UNIQUE KEY uk_payments_student_key (student_id, idempotency_key),
    KEY idx_payments_invoice (invoice_id),
    CONSTRAINT fk_payments_invoice FOREIGN KEY (invoice_id) REFERENCES TUITION_INVOICES (invoice_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_payments_student FOREIGN KEY (student_id) REFERENCES STUDENTS (student_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_payments_installment FOREIGN KEY (installment_id) REFERENCES TUITION_INSTALLMENTS (installment_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_payments_amount CHECK (amount > 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Giao dịch thanh toán học phí';

-- ---------------------------------------------------------------------
-- RECEIPTS: biên lai điện tử phát hành cho mỗi giao dịch nộp thành công
-- ---------------------------------------------------------------------
CREATE TABLE RECEIPTS (
    receipt_id   BIGINT      NOT NULL AUTO_INCREMENT COMMENT 'Mã biên lai',
    receipt_no   VARCHAR(50) NOT NULL                COMMENT 'Số biên lai (BL-<kỳ>-<6 số>)',
    payment_id   BIGINT      NOT NULL                COMMENT 'Giao dịch thanh toán',
    student_id   BIGINT      NOT NULL                COMMENT 'Sinh viên nhận biên lai',
    invoice_id   BIGINT      NOT NULL                COMMENT 'Hóa đơn tương ứng',
    amount       BIGINT      NOT NULL                COMMENT 'Số tiền thu (VND)',
    issued_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời điểm phát hành',
    receipt_data JSON        NOT NULL                COMMENT 'Snapshot dữ liệu biên lai (bất biến)',
    PRIMARY KEY (receipt_id),
    UNIQUE KEY uk_receipts_receipt_no (receipt_no),
    UNIQUE KEY uk_receipts_payment (payment_id),
    KEY idx_receipts_student (student_id),
    CONSTRAINT fk_receipts_payment FOREIGN KEY (payment_id) REFERENCES TUITION_PAYMENTS (payment_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_receipts_student FOREIGN KEY (student_id) REFERENCES STUDENTS (student_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_receipts_invoice FOREIGN KEY (invoice_id) REFERENCES TUITION_INVOICES (invoice_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_receipts_amount CHECK (amount > 0)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Biên lai điện tử thu học phí';

-- ---------------------------------------------------------------------
-- RECEIPT_SEQUENCES: bộ đếm số thứ tự biên lai theo học kỳ
-- ---------------------------------------------------------------------
CREATE TABLE RECEIPT_SEQUENCES (
    semester_id    BIGINT NOT NULL COMMENT 'Mã học kỳ',
    current_number INT    NOT NULL DEFAULT 0 COMMENT 'Số thứ tự biên lai đã cấp',
    PRIMARY KEY (semester_id),
    CONSTRAINT fk_receipt_sequences_semester FOREIGN KEY (semester_id) REFERENCES SEMESTERS (semester_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT 'Số thứ tự sinh biên lai theo học kỳ';
