-- =====================================================================
-- QLDT - Hệ thống Quản lý & Đăng ký Học phần Trực tuyến
-- Lược đồ quan hệ (11 bảng)
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
-- USERS: tài khoản đăng nhập của mọi vai trò (ADMIN, LECTURER, STUDENT)
-- password_hash là chuỗi Bcrypt, không bao giờ xuất hiện trong JSON.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS STUDENT_GRADES;
DROP TABLE IF EXISTS SECTION_GRADE_COMPONENTS;
DROP TABLE IF EXISTS ATTENDANCE_RECORDS;
DROP TABLE IF EXISTS REGISTRATIONS;
DROP TABLE IF EXISTS COURSE_SECTIONS;
DROP TABLE IF EXISTS LECTURERS;
DROP TABLE IF EXISTS STUDENTS;
DROP TABLE IF EXISTS USERS;
DROP TABLE IF EXISTS SUBJECTS;
DROP TABLE IF EXISTS SEMESTERS;
DROP TABLE IF EXISTS ROOMS;

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
    subject_id   BIGINT       NOT NULL AUTO_INCREMENT COMMENT 'Mã môn học (khóa kỹ thuật)',
    subject_code VARCHAR(20)  NOT NULL                COMMENT 'Mã môn học',
    name         VARCHAR(150) NOT NULL                COMMENT 'Tên môn học',
    credits      INT          NOT NULL                COMMENT 'Số tín chỉ',
    description  TEXT             NULL                COMMENT 'Mô tả',
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
    section_id         BIGINT   NOT NULL AUTO_INCREMENT COMMENT 'Mã lớp học phần (khóa kỹ thuật)',
    section_code       VARCHAR(20) NOT NULL            COMMENT 'Mã lớp học phần',
    subject_id         BIGINT   NOT NULL                COMMENT 'Môn học',
    semester_id        BIGINT   NOT NULL                COMMENT 'Học kỳ',
    lecturer_id        BIGINT   NOT NULL                COMMENT 'Giảng viên phụ trách',
    room_id            BIGINT   NOT NULL                COMMENT 'Phòng học',
    day_of_week        TINYINT  NOT NULL                COMMENT 'Thứ (2 = Thứ hai .. 8 = Chủ nhật)',
    start_period       TINYINT  NOT NULL                COMMENT 'Tiết bắt đầu',
    end_period         TINYINT  NOT NULL                COMMENT 'Tiết kết thúc',
    start_week         TINYINT  NOT NULL                COMMENT 'Tuần bắt đầu',
    end_week           TINYINT  NOT NULL                COMMENT 'Tuần kết thúc',
    max_capacity       INT      NOT NULL                COMMENT 'Sĩ số tối đa',
    current_enrollment INT      NOT NULL DEFAULT 0      COMMENT 'Sĩ số hiện tại',
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
