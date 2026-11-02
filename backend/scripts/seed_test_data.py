"""Bộ dữ liệu thử nghiệm cho chức năng quản trị đào tạo (Feature 10).

Chỉ dùng cho cơ sở dữ liệu local. Toàn bộ bản ghi do script tạo đều mang tiền tố
TST/TGV/TSV để có thể nhận diện và dọn sạch:

    python -m scripts.seed_test_data
    python -m scripts.seed_test_data --reset
    python -m scripts.seed_test_data --cleanup

- Không có tham số: tạo hoặc cập nhật bộ dữ liệu, chạy lại nhiều lần an toàn.
- --reset: xóa bộ dữ liệu cũ rồi tạo lại từ đầu.
- --cleanup: chỉ xóa các bản ghi thử nghiệm, không tạo mới.

Bộ dữ liệu bám theo học kỳ đang hoạt động 2026.1 và không chứa ràng buộc môn
tiên quyết/song hành (hai nghiệp vụ này đã được loại bỏ khỏi hệ thống).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.entity import (
    CourseSection,
    Lecturer,
    Registration,
    Role,
    Room,
    Semester,
    Student,
    Subject,
    User,
)
from app.security.password import hash_password

TEST_PASSWORD = "123456"
SEMESTER_CODE = "2026.1"


@dataclass(frozen=True)
class RoomSpec:
    code: str
    building: str
    capacity: int


@dataclass(frozen=True)
class SubjectSpec:
    code: str
    name: str
    credits: int
    description: str


@dataclass(frozen=True)
class AccountSpec:
    username: str
    full_name: str
    email: str
    profile_code: str
    cohort: str | None = None
    major: str | None = None
    department: str | None = None


@dataclass(frozen=True)
class SectionSpec:
    code: str
    subject_code: str
    lecturer_code: str
    room_code: str
    day_of_week: int
    start_period: int
    end_period: int
    start_week: int
    end_week: int
    max_capacity: int
    student_codes: tuple[str, ...] = ()


ROOMS: tuple[RoomSpec, ...] = (
    RoomSpec("TST-101", "TST", 60),
    RoomSpec("TST-102", "TST", 20),
)

SUBJECTS: tuple[SubjectSpec, ...] = (
    SubjectSpec("TST101", "Kiểm thử phần mềm", 3, "Môn học dùng cho bộ dữ liệu Feature 10"),
    SubjectSpec("TST102", "Quản trị cơ sở dữ liệu", 4, "Môn học dùng cho bộ dữ liệu Feature 10"),
    SubjectSpec("TST103", "Kiến trúc hệ thống", 3, "Môn học dùng cho bộ dữ liệu Feature 10"),
    SubjectSpec("TST104", "Thực hành tích hợp", 2, "Môn học dùng cho bộ dữ liệu Feature 10"),
)

LECTURERS: tuple[AccountSpec, ...] = (
    AccountSpec(
        "testgv001",
        "Giảng viên Kiểm thử 1",
        "testgv001@qldt.test",
        "TGV001",
        department="Bộ môn Kiểm thử",
    ),
    AccountSpec(
        "testgv002",
        "Giảng viên Kiểm thử 2",
        "testgv002@qldt.test",
        "TGV002",
        department="Bộ môn Kiểm thử",
    ),
)

STUDENTS: tuple[AccountSpec, ...] = (
    AccountSpec(
        "testsv001",
        "Sinh viên Kiểm thử 1",
        "testsv001@qldt.test",
        "T20260001",
        cohort="K2026",
        major="Khoa học máy tính",
    ),
    AccountSpec(
        "testsv002",
        "Sinh viên Kiểm thử 2",
        "testsv002@qldt.test",
        "T20260002",
        cohort="K2026",
        major="Khoa học máy tính",
    ),
    AccountSpec(
        "testsv003",
        "Sinh viên Kiểm thử 3",
        "testsv003@qldt.test",
        "T20260003",
        cohort="K2026",
        major="Kỹ thuật phần mềm",
    ),
)

SECTIONS: tuple[SectionSpec, ...] = (
    SectionSpec("TST-S01", "TST101", "TGV001", "TST-101", 2, 1, 3, 1, 15, 40),
    SectionSpec("TST-S02", "TST102", "TGV002", "TST-101", 3, 4, 6, 1, 15, 40),
    SectionSpec("TST-S03", "TST103", "TGV001", "TST-102", 4, 1, 3, 1, 15, 1),
    SectionSpec("TST-S04", "TST104", "TGV002", "TST-101", 5, 7, 9, 1, 15, 40),
    SectionSpec("TST-S05", "TST101", "TGV001", "TST-102", 6, 10, 12, 1, 15, 40),
)

REGISTRATIONS: dict[str, tuple[str, ...]] = {
    "T20260001": ("TST-S01", "TST-S02", "TST-S03", "TST-S04"),
    "T20260002": ("TST-S01", "TST-S02", "TST-S04"),
    "T20260003": ("TST-S01",),
}


def _get_or_create_user(db: Session, spec: AccountSpec, role: Role) -> User:
    user = db.scalars(select(User).where(User.username == spec.username)).first()
    if user is None:
        user = User(
            username=spec.username,
            password_hash=hash_password(TEST_PASSWORD),
            full_name=spec.full_name,
            email=spec.email,
            role=role,
        )
        db.add(user)
        db.flush()
    return user


def _get_or_create_lecturer(db: Session, user: User, spec: AccountSpec) -> Lecturer:
    lecturer = db.scalars(
        select(Lecturer).where(Lecturer.lecturer_code == spec.profile_code)
    ).first()
    if lecturer is None:
        lecturer = Lecturer(
            user_id=user.id,
            lecturer_code=spec.profile_code,
            department=spec.department,
        )
        db.add(lecturer)
        db.flush()
    return lecturer


def _get_or_create_student(db: Session, user: User, spec: AccountSpec) -> Student:
    student = db.scalars(select(Student).where(Student.student_code == spec.profile_code)).first()
    if student is None:
        student = Student(
            user_id=user.id,
            student_code=spec.profile_code,
            cohort=spec.cohort,
            major=spec.major,
        )
        db.add(student)
        db.flush()
    return student


def _get_or_create_room(db: Session, spec: RoomSpec) -> Room:
    room = db.scalars(select(Room).where(Room.room_code == spec.code)).first()
    if room is None:
        room = Room(room_code=spec.code, building=spec.building, capacity=spec.capacity)
        db.add(room)
        db.flush()
    else:
        room.building = spec.building
        room.capacity = spec.capacity
    return room


def _get_or_create_subject(db: Session, spec: SubjectSpec) -> Subject:
    subject = db.scalars(select(Subject).where(Subject.subject_code == spec.code)).first()
    if subject is None:
        subject = Subject(
            subject_code=spec.code,
            name=spec.name,
            credits=spec.credits,
            description=spec.description,
        )
        db.add(subject)
        db.flush()
    else:
        subject.name = spec.name
        subject.credits = spec.credits
        subject.description = spec.description
    return subject


def _get_or_create_section(
    db: Session,
    spec: SectionSpec,
    subjects: dict[str, Subject],
    lecturers: dict[str, Lecturer],
    rooms: dict[str, Room],
    semester: Semester,
) -> CourseSection:
    section = db.scalars(
        select(CourseSection).where(CourseSection.section_code == spec.code)
    ).first()
    if section is None:
        section = CourseSection(section_code=spec.code, current_enrollment=0)
        db.add(section)
    section.subject_id = subjects[spec.subject_code].id
    section.semester_id = semester.id
    section.lecturer_id = lecturers[spec.lecturer_code].id
    section.room_id = rooms[spec.room_code].id
    section.day_of_week = spec.day_of_week
    section.start_period = spec.start_period
    section.end_period = spec.end_period
    section.start_week = spec.start_week
    section.end_week = spec.end_week
    section.max_capacity = spec.max_capacity
    db.flush()
    return section


def _ensure_registration(db: Session, student: Student, section: CourseSection) -> None:
    existing = db.scalars(
        select(Registration).where(
            Registration.student_id == student.id,
            Registration.section_id == section.id,
        )
    ).first()
    if existing is None:
        db.add(Registration(student_id=student.id, section_id=section.id))
        db.flush()


def _recompute_enrollment(db: Session, sections: list[CourseSection]) -> None:
    for section in sections:
        count = db.scalar(
            select(func.count())
            .select_from(Registration)
            .where(Registration.section_id == section.id)
        )
        section.current_enrollment = int(count or 0)


def _assert_no_conflicts(sections: list[CourseSection]) -> None:
    for index, first in enumerate(sections):
        for second in sections[index + 1 :]:
            if first.semester_id != second.semester_id:
                continue
            if first.day_of_week != second.day_of_week:
                continue
            week_overlap = (
                first.start_week <= second.end_week and second.start_week <= first.end_week
            )
            period_overlap = (
                first.start_period <= second.end_period and second.start_period <= first.end_period
            )
            if not (week_overlap and period_overlap):
                continue
            if first.room_id == second.room_id:
                raise RuntimeError(
                    f"Hai lớp thử nghiệm trùng phòng: {first.section_code} / {second.section_code}"
                )
            if first.lecturer_id == second.lecturer_id:
                raise RuntimeError(
                    f"Hai lớp thử nghiệm trùng giảng viên: {first.section_code} / {second.section_code}"
                )


def cleanup(db: Session) -> dict[str, int]:
    usernames = [spec.username for spec in LECTURERS + STUDENTS]
    subject_codes = [spec.code for spec in SUBJECTS]
    section_codes = [spec.code for spec in SECTIONS]
    room_codes = [spec.code for spec in ROOMS]
    lecturer_codes = [spec.profile_code for spec in LECTURERS]
    student_codes = [spec.profile_code for spec in STUDENTS]

    section_ids = list(
        db.scalars(select(CourseSection.id).where(CourseSection.section_code.in_(section_codes)))
    )
    student_ids = list(
        db.scalars(select(Student.id).where(Student.student_code.in_(student_codes)))
    )
    lecturer_ids = list(
        db.scalars(select(Lecturer.id).where(Lecturer.lecturer_code.in_(lecturer_codes)))
    )
    user_ids = list(db.scalars(select(User.id).where(User.username.in_(usernames))))

    removed = {"registrations": 0, "sections": 0, "subjects": 0, "accounts": 0, "rooms": 0}
    if section_ids or student_ids:
        result = db.execute(
            delete(Registration).where(
                or_(
                    Registration.section_id.in_(section_ids or [-1]),
                    Registration.student_id.in_(student_ids or [-1]),
                )
            )
        )
        removed["registrations"] = result.rowcount or 0

    if section_ids:
        result = db.execute(delete(CourseSection).where(CourseSection.id.in_(section_ids)))
        removed["sections"] = result.rowcount or 0
    if subject_codes:
        result = db.execute(delete(Subject).where(Subject.subject_code.in_(subject_codes)))
        removed["subjects"] = result.rowcount or 0
    if student_ids:
        db.execute(delete(Student).where(Student.id.in_(student_ids)))
    if lecturer_ids:
        db.execute(delete(Lecturer).where(Lecturer.id.in_(lecturer_ids)))
    if user_ids:
        result = db.execute(delete(User).where(User.id.in_(user_ids)))
        removed["accounts"] = result.rowcount or 0
    if room_codes:
        result = db.execute(delete(Room).where(Room.room_code.in_(room_codes)))
        removed["rooms"] = result.rowcount or 0
    db.commit()
    return removed


def seed(db: Session) -> dict[str, int]:
    semester = db.scalars(select(Semester).where(Semester.semester_code == SEMESTER_CODE)).first()
    if semester is None:
        raise RuntimeError(
            f"Không tìm thấy học kỳ {SEMESTER_CODE}. Hãy chạy python -m scripts.seed trước."
        )

    rooms = {spec.code: _get_or_create_room(db, spec) for spec in ROOMS}
    subjects = {spec.code: _get_or_create_subject(db, spec) for spec in SUBJECTS}

    lecturers: dict[str, Lecturer] = {}
    for spec in LECTURERS:
        user = _get_or_create_user(db, spec, Role.LECTURER)
        lecturers[spec.profile_code] = _get_or_create_lecturer(db, user, spec)

    students: dict[str, Student] = {}
    for spec in STUDENTS:
        user = _get_or_create_user(db, spec, Role.STUDENT)
        students[spec.profile_code] = _get_or_create_student(db, user, spec)

    sections: dict[str, CourseSection] = {}
    for spec in SECTIONS:
        sections[spec.code] = _get_or_create_section(db, spec, subjects, lecturers, rooms, semester)

    for student_code, section_codes in REGISTRATIONS.items():
        for section_code in section_codes:
            _ensure_registration(db, students[student_code], sections[section_code])

    _recompute_enrollment(db, list(sections.values()))
    _assert_no_conflicts(list(sections.values()))
    db.commit()

    return {
        "rooms": len(rooms),
        "subjects": len(subjects),
        "lecturers": len(lecturers),
        "students": len(students),
        "sections": len(sections),
        "registrations": sum(len(codes) for codes in REGISTRATIONS.values()),
    }


def print_summary(summary: dict[str, int], semester: Semester | None = None) -> None:
    print("Bộ dữ liệu thử nghiệm Feature 10 đã sẵn sàng.")
    if semester is not None:
        print(f"  Học kỳ: {semester.semester_code} ({semester.name})")
    print(
        "  Phòng: {rooms} · Môn: {subjects} · Giảng viên: {lecturers} · "
        "Sinh viên: {students} · Lớp: {sections} · Đăng ký: {registrations}".format(**summary)
    )
    print("  Tài khoản: admin/admin (có sẵn), testgv001/123456, testsv001/123456")
    print("  Lớp đầy: TST-S03 (sĩ số 1). Lớp trống: TST-S05. Lớp nhiều sinh viên: TST-S01.")
    print("  Dọn dữ liệu: python -m scripts.seed_test_data --cleanup")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bộ dữ liệu thử nghiệm quản trị đào tạo")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--reset", action="store_true", help="Xóa rồi tạo lại bộ dữ liệu")
    group.add_argument("--cleanup", action="store_true", help="Chỉ xóa bộ dữ liệu thử nghiệm")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.cleanup:
            removed = cleanup(db)
            print(f"Đã dọn bộ dữ liệu thử nghiệm: {removed}")
            return
        if args.reset:
            removed = cleanup(db)
            print(f"Đã dọn bộ dữ liệu cũ: {removed}")
        summary = seed(db)
        semester = db.scalars(
            select(Semester).where(Semester.semester_code == SEMESTER_CODE)
        ).first()
        print_summary(summary, semester)


if __name__ == "__main__":
    main()
