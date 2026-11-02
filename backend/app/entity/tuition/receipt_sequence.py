from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.entity.base import Base, BigInt


class ReceiptSequence(Base):
    __tablename__ = "RECEIPT_SEQUENCES"

    semester_id: Mapped[int] = mapped_column(
        BigInt, ForeignKey("SEMESTERS.semester_id", ondelete="RESTRICT"), primary_key=True
    )
    current_number: Mapped[int] = mapped_column(default=0, nullable=False)
