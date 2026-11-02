from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entity.base import Base, BigInt
from app.entity.catalog.semester import Semester


class TuitionInstallment(Base):
    __tablename__ = "TUITION_INSTALLMENTS"
    __table_args__ = (
        UniqueConstraint("semester_id", "installment_order", name="uq_installment_semester_order"),
        CheckConstraint("installment_order > 0", name="installment_order_positive"),
        CheckConstraint(
            "(percentage IS NOT NULL AND fixed_amount IS NULL) OR "
            "(percentage IS NULL AND fixed_amount IS NOT NULL)",
            name="amount_basis_exactly_one",
        ),
        CheckConstraint(
            "percentage IS NULL OR (percentage >= 0 AND percentage <= 100)",
            name="percentage_range",
        ),
        CheckConstraint(
            "fixed_amount IS NULL OR fixed_amount >= 0", name="fixed_amount_non_negative"
        ),
    )

    id: Mapped[int] = mapped_column("installment_id", BigInt, primary_key=True, autoincrement=True)
    semester_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("SEMESTERS.semester_id", ondelete="RESTRICT"), nullable=False
    )
    installment_order: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    fixed_amount: Mapped[int | None] = mapped_column(BigInt, nullable=True)

    semester: Mapped[Semester] = relationship()
