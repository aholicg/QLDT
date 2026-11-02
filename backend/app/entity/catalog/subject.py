from decimal import Decimal

from sqlalchemy import CheckConstraint, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.entity.base import Base, BigInt


class Subject(Base):
    __tablename__ = "SUBJECTS"
    __table_args__ = (CheckConstraint("credits > 0", name="credits_positive"),)

    id: Mapped[int] = mapped_column("subject_id", BigInt, primary_key=True, autoincrement=True)
    subject_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    credits: Mapped[int] = mapped_column(nullable=False)
    tuition_credits: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    description: Mapped[str | None] = mapped_column(Text)

    @property
    def effective_tuition_credits(self) -> Decimal:
        if self.tuition_credits is not None:
            return Decimal(str(self.tuition_credits))
        return Decimal(self.credits)
