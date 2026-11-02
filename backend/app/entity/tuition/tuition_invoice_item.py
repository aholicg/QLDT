from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entity.base import Base, BigInt
from app.entity.catalog.subject import Subject

if TYPE_CHECKING:
    from app.entity.tuition.tuition_invoice import TuitionInvoice


class TuitionInvoiceItem(Base):
    __tablename__ = "TUITION_INVOICE_ITEMS"
    __table_args__ = (
        CheckConstraint("credits > 0", name="item_credits_positive"),
        CheckConstraint("tuition_credits > 0", name="item_tuition_credits_positive"),
        CheckConstraint("price_per_credit > 0", name="item_price_positive"),
        CheckConstraint("amount >= 0", name="item_amount_non_negative"),
        Index("idx_invoice_items_invoice_id", "invoice_id"),
    )

    id: Mapped[int] = mapped_column("item_id", BigInt, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("TUITION_INVOICES.invoice_id", ondelete="RESTRICT"), nullable=False
    )
    subject_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("SUBJECTS.subject_id", ondelete="RESTRICT"), nullable=False
    )
    subject_code: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_name: Mapped[str] = mapped_column(String(150), nullable=False)
    credits: Mapped[int] = mapped_column(nullable=False)
    tuition_credits: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    price_per_credit: Mapped[int] = mapped_column(BigInt, nullable=False)
    amount: Mapped[int] = mapped_column(BigInt, nullable=False)

    invoice: Mapped["TuitionInvoice"] = relationship(back_populates="items")
    subject: Mapped[Subject] = relationship()
