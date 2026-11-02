from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from pydantic import Field, field_validator, model_validator

from app.dto.common import CamelModel


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    EXCUSED = "EXCUSED"


class AttendanceEntry(CamelModel):
    student_id: int
    student_code: str
    full_name: str
    email: str | None
    status: AttendanceStatus | None


class AttendanceSheet(CamelModel):
    section_id: int
    section_code: str
    class_date: date
    scheduled_dates: list[date]
    items: list[AttendanceEntry]


class AttendanceUpdateItem(CamelModel):
    student_id: int
    status: AttendanceStatus


class AttendanceUpdateRequest(CamelModel):
    class_date: date
    items: list[AttendanceUpdateItem]


class GradeComponentInput(CamelModel):
    name: str = Field(min_length=1, max_length=80)
    weight_percentage: Decimal = Field(gt=0, le=100, max_digits=5, decimal_places=2)
    max_score: Decimal = Field(gt=0, le=100, max_digits=5, decimal_places=2)


class GradeComponentsRequest(CamelModel):
    items: list[GradeComponentInput] = Field(min_length=1, max_length=10)

    @field_validator("items")
    @classmethod
    def unique_component_names(cls, items: list[GradeComponentInput]):
        names = [item.name.strip().casefold() for item in items]
        if len(set(names)) != len(names):
            raise ValueError("Tên cột điểm không được trùng nhau")
        return items

    @model_validator(mode="after")
    def weights_total_one_hundred(self):
        if sum(item.weight_percentage for item in self.items) != Decimal("100"):
            raise ValueError("Tổng trọng số các cột điểm phải bằng 100%")
        return self


class GradeComponent(CamelModel):
    id: int
    name: str
    weight_percentage: float
    max_score: float
    sort_order: int


class GradeUpdateItem(CamelModel):
    student_id: int
    scores: dict[int, Decimal | None]


class GradeUpdateRequest(CamelModel):
    items: list[GradeUpdateItem]


class StudentGradeRow(CamelModel):
    student_id: int
    student_code: str
    full_name: str
    email: str | None
    scores: dict[int, float | None]
    final_score: float | None


class GradeBook(CamelModel):
    section_id: int
    section_code: str
    components: list[GradeComponent]
    items: list[StudentGradeRow]


def round_final_score(value: Decimal) -> Decimal:
    """Round to the nearest 0.5; ROUND_HALF_UP makes exact ties round upward."""
    return (value * 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / 2
