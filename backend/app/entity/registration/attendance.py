import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.entity.base import Base, BigInt


class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    EXCUSED = "EXCUSED"


class AttendanceRecord(Base):
    __tablename__ = "ATTENDANCE_RECORDS"
    __table_args__ = (
        UniqueConstraint(
            "section_id", "student_id", "class_date", name="uq_attendance_section_student_date"
        ),
        Index("ix_attendance_section_date", "section_id", "class_date"),
    )

    id: Mapped[int] = mapped_column("attendance_id", BigInt, primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(
        BigInt,
        ForeignKey("COURSE_SECTIONS.section_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        BigInt,
        ForeignKey("STUDENTS.student_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    class_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(
        SAEnum(AttendanceStatus, name="attendance_status"), nullable=False
    )
    marked_by_user_id: Mapped[int] = mapped_column(
        BigInt,
        ForeignKey("USERS.user_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class GradeComponent(Base):
    __tablename__ = "SECTION_GRADE_COMPONENTS"
    __table_args__ = (
        CheckConstraint(
            "weight_percentage > 0 AND weight_percentage <= 100",
            name="weight_percentage_range",
        ),
        CheckConstraint("max_score > 0", name="max_score_positive"),
        UniqueConstraint("section_id", "name", name="uq_grade_components_section_name"),
        UniqueConstraint("section_id", "sort_order", name="uq_grade_components_section_order"),
        Index("ix_grade_components_section", "section_id"),
    )

    id: Mapped[int] = mapped_column("component_id", BigInt, primary_key=True, autoincrement=True)
    section_id: Mapped[int] = mapped_column(
        BigInt,
        ForeignKey("COURSE_SECTIONS.section_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    weight_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    max_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(nullable=False)


class StudentGrade(Base):
    __tablename__ = "STUDENT_GRADES"
    __table_args__ = (
        CheckConstraint("score >= 0", name="score_nonnegative"),
        UniqueConstraint("component_id", "student_id", name="uq_student_grades_component_student"),
        Index("ix_student_grades_student", "student_id"),
    )

    id: Mapped[int] = mapped_column("grade_id", BigInt, primary_key=True, autoincrement=True)
    component_id: Mapped[int] = mapped_column(
        BigInt,
        ForeignKey(
            "SECTION_GRADE_COMPONENTS.component_id", onupdate="CASCADE", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        BigInt,
        ForeignKey("STUDENTS.student_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    updated_by_user_id: Mapped[int] = mapped_column(
        BigInt,
        ForeignKey("USERS.user_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
