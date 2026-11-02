from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entity.auth.student import Student
from app.entity.base import Base, BigInt
from app.entity.tuition.tuition_installment import TuitionInstallment

if TYPE_CHECKING:
    from app.entity.tuition.receipt import Receipt
    from app.entity.tuition.tuition_invoice import TuitionInvoice


class TuitionPayment(Base):
    __tablename__ = "TUITION_PAYMENTS"
    __table_args__ = (
        UniqueConstraint("student_id", "idempotency_key", name="uq_payment_student_key"),
        CheckConstraint("amount > 0", name="payment_amount_positive"),
        Index("idx_tuition_payments_invoice", "invoice_id"),
    )

    id: Mapped[int] = mapped_column("payment_id", BigInt, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("TUITION_INVOICES.invoice_id", ondelete="RESTRICT"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("STUDENTS.student_id", ondelete="RESTRICT"), nullable=False
    )
    installment_id: Mapped[int | None] = mapped_column(
        BigInt,
        ForeignKey("TUITION_INSTALLMENTS.installment_id", ondelete="RESTRICT"),
        nullable=True,
    )
    amount: Mapped[int] = mapped_column(BigInt, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), default="SIMULATED", nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    invoice: Mapped["TuitionInvoice"] = relationship(back_populates="payments")
    student: Mapped[Student] = relationship()
    installment: Mapped[TuitionInstallment | None] = relationship()
    receipt: Mapped["Receipt"] = relationship(back_populates="payment", uselist=False)
