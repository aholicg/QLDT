import datetime as dt
from typing import Literal

from pydantic import Field, model_validator

from app.dto.common import CamelModel


class TimetableItem(CamelModel):
    section_id: int
    section_code: str
    subject_code: str
    subject_name: str
    day_of_week: int
    date: dt.date  # ngày học cụ thể trong tuần được chọn
    start_period: int
    end_period: int
    room_code: str
    lecturer_name: str
    start_week: int
    end_week: int


class Timetable(CamelModel):
    semester_id: int
    week: int
    week_start_date: dt.date  # Thứ hai
    week_end_date: dt.date  # Chủ nhật
    items: list[TimetableItem]  # sắp theo dayOfWeek rồi startPeriod


class ScheduleSlot(CamelModel):
    section_code: str | None = None
    day_of_week: int = Field(..., ge=2, le=8)
    start_period: int = Field(..., ge=1, le=12)
    end_period: int = Field(..., ge=1, le=12)
    start_week: int = Field(default=1, ge=1)
    end_week: int = Field(default=1, ge=1)
    room_id: int | None = None
    lecturer_id: int | None = None

    @model_validator(mode="after")
    def validate_ranges(self) -> "ScheduleSlot":
        if self.end_period < self.start_period:
            raise ValueError("Tiết kết thúc phải lớn hơn hoặc bằng tiết bắt đầu")
        if self.end_week < self.start_week:
            raise ValueError("Tuần kết thúc phải lớn hơn hoặc bằng tuần bắt đầu")
        return self


class ConflictRange(CamelModel):
    start: int
    end: int


class ScheduleConflict(CamelModel):
    type: Literal["STUDENT", "LECTURER", "ROOM"]
    section_a: str
    section_b: str
    day_of_week: int
    periods: ConflictRange
    weeks: ConflictRange
