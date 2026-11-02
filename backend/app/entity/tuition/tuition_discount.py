from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entity.auth.student import Student
from app.entity.base import Base, BigInt
from app.entity.catalog.semester import Semester


class TuitionDiscount(Base):
    __tablename__ = "TUITION_DISCOUNTS"
    __table_args__ = (
        CheckConstraint(
            "discount_percent >= 0 AND discount_percent <= 100", name="discount_percent_range"
        ),
        CheckConstraint("fixed_amount >= 0", name="fixed_amount_non_negative"),
        Index("idx_tuition_discounts_student_semester", "student_id", "semester_id"),
    )

    id: Mapped[int] = mapped_column("discount_id", BigInt, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("STUDENTS.student_id", ondelete="RESTRICT"), nullable=False
    )
    semester_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("SEMESTERS.semester_id", ondelete="RESTRICT"), nullable=False
    )
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("0.00"), nullable=False
    )
    fixed_amount: Mapped[int] = mapped_column(BigInt, default=0, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    granted_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    student: Mapped[Student] = relationship()
    semester: Mapped[Semester] = relationship()
