import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entity.auth.student import Student
from app.entity.base import Base, BigInt
from app.entity.catalog.semester import Semester

if TYPE_CHECKING:
    from app.entity.tuition.tuition_invoice_item import TuitionInvoiceItem
    from app.entity.tuition.tuition_payment import TuitionPayment


class InvoiceStatus(str, enum.Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class TuitionInvoice(Base):
    __tablename__ = "TUITION_INVOICES"
    __table_args__ = (
        UniqueConstraint("student_id", "semester_id", name="uq_invoice_student_semester"),
        CheckConstraint("total_tuition >= 0", name="total_tuition_non_negative"),
        CheckConstraint("total_discount >= 0", name="total_discount_non_negative"),
        CheckConstraint("amount_due >= 0", name="amount_due_non_negative"),
        CheckConstraint("amount_paid >= 0", name="amount_paid_non_negative"),
        Index("idx_tuition_invoices_student_semester", "student_id", "semester_id"),
    )

    id: Mapped[int] = mapped_column("invoice_id", BigInt, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("STUDENTS.student_id", ondelete="RESTRICT"), nullable=False
    )
    semester_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("SEMESTERS.semester_id", ondelete="RESTRICT"), nullable=False
    )
    total_tuition: Mapped[int] = mapped_column(BigInt, default=0, nullable=False)
    total_discount: Mapped[int] = mapped_column(BigInt, default=0, nullable=False)
    amount_due: Mapped[int] = mapped_column(BigInt, default=0, nullable=False)
    amount_paid: Mapped[int] = mapped_column(BigInt, default=0, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"), default=InvoiceStatus.UNPAID, nullable=False
    )
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    student: Mapped[Student] = relationship()
    semester: Mapped[Semester] = relationship()
    items: Mapped[list["TuitionInvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    payments: Mapped[list["TuitionPayment"]] = relationship(back_populates="invoice")
