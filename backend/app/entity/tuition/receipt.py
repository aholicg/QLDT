from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entity.auth.student import Student
from app.entity.base import Base, BigInt
from app.entity.tuition.tuition_invoice import TuitionInvoice

if TYPE_CHECKING:
    from app.entity.tuition.tuition_payment import TuitionPayment


class Receipt(Base):
    __tablename__ = "RECEIPTS"
    __table_args__ = (
        UniqueConstraint("receipt_no", name="uq_receipt_no"),
        UniqueConstraint("payment_id", name="uq_receipt_payment"),
        CheckConstraint("amount > 0", name="receipt_amount_positive"),
    )

    id: Mapped[int] = mapped_column("receipt_id", BigInt, primary_key=True, autoincrement=True)
    receipt_no: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("TUITION_PAYMENTS.payment_id", ondelete="RESTRICT"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("STUDENTS.student_id", ondelete="RESTRICT"), nullable=False
    )
    invoice_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("TUITION_INVOICES.invoice_id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[int] = mapped_column(BigInt, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    receipt_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    payment: Mapped["TuitionPayment"] = relationship(back_populates="receipt")
    student: Mapped[Student] = relationship()
    invoice: Mapped[TuitionInvoice] = relationship()
