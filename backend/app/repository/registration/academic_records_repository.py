from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.entity.auth.student import Student
from app.entity.registration.attendance import (
    AttendanceRecord,
    AttendanceStatus,
    GradeComponent,
    StudentGrade,
)
from app.entity.registration.registration import Registration
from app.repository.base import BaseRepository


class AcademicRecordsRepository(BaseRepository):
    def section_has_academic_records(self, section_id: int) -> bool:
        attendance_exists = self.db.scalar(
            select(AttendanceRecord.id).where(AttendanceRecord.section_id == section_id).limit(1)
        )
        component_exists = self.db.scalar(
            select(GradeComponent.id).where(GradeComponent.section_id == section_id).limit(1)
        )
        return attendance_exists is not None or component_exists is not None

    def list_roster(self, section_id: int) -> list[Registration]:
        statement = (
            select(Registration)
            .options(
                joinedload(Registration.student).joinedload(Student.user),
            )
            .where(Registration.section_id == section_id)
            .join(Registration.student)
            .order_by(Student.student_code)
        )
        return list(self.db.scalars(statement).unique().all())

    def attendance_for_date(self, section_id: int, class_date: date) -> dict[int, AttendanceRecord]:
        statement = select(AttendanceRecord).where(
            AttendanceRecord.section_id == section_id,
            AttendanceRecord.class_date == class_date,
        )
        return {record.student_id: record for record in self.db.scalars(statement).all()}

    def all_attendance(self, section_id: int) -> list[AttendanceRecord]:
        statement = (
            select(AttendanceRecord)
            .where(AttendanceRecord.section_id == section_id)
            .order_by(AttendanceRecord.class_date, AttendanceRecord.student_id)
        )
        return list(self.db.scalars(statement).all())

    def save_attendance(
        self,
        *,
        section_id: int,
        student_id: int,
        class_date: date,
        status: AttendanceStatus,
        marked_by_user_id: int,
    ) -> AttendanceRecord:
        record = self.db.scalars(
            select(AttendanceRecord).where(
                AttendanceRecord.section_id == section_id,
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.class_date == class_date,
            )
        ).first()
        if record is None:
            record = AttendanceRecord(
                section_id=section_id,
                student_id=student_id,
                class_date=class_date,
                status=status,
                marked_by_user_id=marked_by_user_id,
            )
            self.db.add(record)
        else:
            record.status = status
            record.marked_by_user_id = marked_by_user_id
        self.db.flush()
        return record

    def list_components(self, section_id: int) -> list[GradeComponent]:
        statement = (
            select(GradeComponent)
            .where(GradeComponent.section_id == section_id)
            .order_by(GradeComponent.sort_order, GradeComponent.id)
        )
        return list(self.db.scalars(statement).all())

    def grade_scores(self, component_ids: list[int]) -> list[StudentGrade]:
        if not component_ids:
            return []
        statement = select(StudentGrade).where(StudentGrade.component_id.in_(component_ids))
        return list(self.db.scalars(statement).all())

    def has_grade_scores(self, component_ids: list[int]) -> bool:
        if not component_ids:
            return False
        statement = (
            select(StudentGrade.id).where(StudentGrade.component_id.in_(component_ids)).limit(1)
        )
        return self.db.scalar(statement) is not None

    def delete_components(self, components: list[GradeComponent]) -> None:
        for component in components:
            self.db.delete(component)
        self.db.flush()

    def add_components(self, components: list[GradeComponent]) -> None:
        self.db.add_all(components)
        self.db.flush()

    def save_grade(
        self,
        *,
        component_id: int,
        student_id: int,
        score: Decimal | None,
        updated_by_user_id: int,
    ) -> None:
        grade = self.db.scalars(
            select(StudentGrade).where(
                StudentGrade.component_id == component_id,
                StudentGrade.student_id == student_id,
            )
        ).first()
        if score is None:
            if grade is not None:
                self.db.delete(grade)
            return
        if grade is None:
            grade = StudentGrade(
                component_id=component_id,
                student_id=student_id,
                score=score,
                updated_by_user_id=updated_by_user_id,
            )
            self.db.add(grade)
        else:
            grade.score = score
            grade.updated_by_user_id = updated_by_user_id
