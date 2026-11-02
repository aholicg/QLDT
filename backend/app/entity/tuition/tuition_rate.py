from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entity.base import Base, BigInt
from app.entity.catalog.semester import Semester


class TuitionRate(Base):
    __tablename__ = "TUITION_RATES"
    __table_args__ = (
        CheckConstraint("price_per_credit > 0", name="price_positive"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="effective_range_valid",
        ),
        Index("idx_tuition_rates_lookup", "semester_id", "cohort", "major"),
        Index(
            "idx_tuition_rates_effective_lookup",
            "semester_id",
            "cohort",
            "major",
            "effective_from",
            "effective_to",
        ),
    )

    id: Mapped[int] = mapped_column("rate_id", BigInt, primary_key=True, autoincrement=True)
    semester_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("SEMESTERS.semester_id", ondelete="RESTRICT"), nullable=False
    )
    cohort: Mapped[str | None] = mapped_column(String(10), nullable=True)
    major: Mapped[str | None] = mapped_column(String(100), nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    price_per_credit: Mapped[int] = mapped_column(BigInt, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    semester: Mapped[Semester] = relationship()
