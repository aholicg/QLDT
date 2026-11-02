from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.entity.auth.lecturer import Lecturer
from app.entity.auth.student import Student
from app.entity.catalog.course_section import CourseSection
from app.entity.catalog.subject import Subject
from app.entity.registration.registration import Registration
from app.repository.base import BaseRepository


class RegistrationRepository(BaseRepository):
    def get_by_id(self, registration_id: int) -> Registration | None:
        stmt = (
            select(Registration)
            .options(
                joinedload(Registration.section).joinedload(CourseSection.subject),
                joinedload(Registration.section).joinedload(CourseSection.semester),
                joinedload(Registration.section)
                .joinedload(CourseSection.lecturer)
                .joinedload(Lecturer.user),
                joinedload(Registration.section).joinedload(CourseSection.room),
                joinedload(Registration.student),
            )
            .where(Registration.id == registration_id)
        )
        return self.db.scalars(stmt).first()

    def add(self, registration: Registration) -> Registration:
        self.db.add(registration)
        self.db.flush()
        return registration

    def delete(self, registration: Registration) -> None:
        self.db.delete(registration)
        self.db.flush()

    def exists(self, student_id: int, section_id: int) -> bool:
        stmt = select(Registration.id).where(
            Registration.student_id == student_id, Registration.section_id == section_id
        )
        return self.db.scalars(stmt).first() is not None

    def find_same_subject(
        self, student_id: int, subject_id: int, semester_id: int
    ) -> Registration | None:
        """Sinh viên đã đăng ký lớp khác của cùng môn trong học kỳ chưa?"""
        stmt = (
            select(Registration)
            .join(CourseSection, Registration.section_id == CourseSection.id)
            .where(
                Registration.student_id == student_id,
                CourseSection.subject_id == subject_id,
                CourseSection.semester_id == semester_id,
            )
        )
        return self.db.scalars(stmt).first()

    def find_schedule_conflicts(
        self, student_id: int, section: CourseSection
    ) -> list[CourseSection]:
        """Các lớp sinh viên đã đăng ký mà trùng thứ + giao tiết + giao tuần với `section`."""
        stmt = (
            select(CourseSection)
            .join(Registration, Registration.section_id == CourseSection.id)
            .where(
                Registration.student_id == student_id,
                CourseSection.semester_id == section.semester_id,
                CourseSection.id != section.id,
                CourseSection.day_of_week == section.day_of_week,
            )
        )
        candidates = list(self.db.scalars(stmt).all())
        if not candidates:
            return []

        from app.service.timetable.conflict_engine import find_conflicts

        conflicts = find_conflicts(
            [
                {
                    "sectionCode": slot.section_code,
                    "dayOfWeek": slot.day_of_week,
                    "startPeriod": slot.start_period,
                    "endPeriod": slot.end_period,
                    "startWeek": slot.start_week,
                    "endWeek": slot.end_week,
                }
                for slot in [section, *candidates]
            ]
        )
        if not conflicts:
            return []

        target_code = section.section_code
        conflicting_codes = {
            c["sectionA"] if c["sectionB"] == target_code else c["sectionB"]
            for c in conflicts
            if c["sectionA"] == target_code or c["sectionB"] == target_code
        }
        return [c for c in candidates if c.section_code in conflicting_codes]

    def total_credits(self, student_id: int, semester_id: int) -> int:
        stmt = (
            select(func.coalesce(func.sum(Subject.credits), 0))
            .select_from(Registration)
            .join(CourseSection, Registration.section_id == CourseSection.id)
            .join(Subject, CourseSection.subject_id == Subject.id)
            .where(
                Registration.student_id == student_id,
                CourseSection.semester_id == semester_id,
            )
        )
        return int(self.db.scalar(stmt) or 0)

    def list_by_student(self, student_id: int, semester_id: int) -> list[Registration]:
        stmt = (
            select(Registration)
            .join(CourseSection, Registration.section_id == CourseSection.id)
            .options(
                joinedload(Registration.section).joinedload(CourseSection.subject),
                joinedload(Registration.section).joinedload(CourseSection.semester),
                joinedload(Registration.section)
                .joinedload(CourseSection.lecturer)
                .joinedload(Lecturer.user),
                joinedload(Registration.section).joinedload(CourseSection.room),
            )
            .where(
                Registration.student_id == student_id,
                CourseSection.semester_id == semester_id,
            )
            .order_by(
                CourseSection.day_of_week.asc(),
                CourseSection.start_period.asc(),
                Registration.registered_at.asc(),
                Registration.id.asc(),
            )
        )
        return list(self.db.scalars(stmt).all())

    def list_students_of_section(self, section_id: int) -> list[Registration]:
        stmt = (
            select(Registration)
            .options(
                joinedload(Registration.student).joinedload(Student.user),
            )
            .where(Registration.section_id == section_id)
            .order_by(Registration.registered_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def registered_section_ids_for_student(self, student_id: int, semester_id: int) -> set[int]:
        stmt = (
            select(Registration.section_id)
            .join(CourseSection, Registration.section_id == CourseSection.id)
            .where(
                Registration.student_id == student_id,
                CourseSection.semester_id == semester_id,
            )
        )
        return set(self.db.scalars(stmt).all())
