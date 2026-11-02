from itertools import product
from typing import Any

from fastapi import APIRouter, Body, Query
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.database import DbSession
from app.dto.catalog.catalog import Section
from app.dto.common import ItemList
from app.dto.timetable.timetable import ScheduleConflict, ScheduleSlot, Timetable
from app.entity.catalog.course_section import CourseSection
from app.security.dependencies import AdminUser, LecturerUser, StudentUser
from app.service.catalog.semester_service import SemesterService
from app.service.timetable.timetable_service import TimetableService

router = APIRouter(tags=["timetable"])


@router.get(
    "/students/me/timetable", response_model=Timetable, summary="Thời khóa biểu sinh viên (UC007)"
)
def student_timetable(
    user: StudentUser,
    db: DbSession,
    semester_id: int | None = Query(None, alias="semesterId"),
    week: int | None = Query(None, ge=1),
):
    if semester_id is None:
        semester_id = SemesterService(db).get_current().id
    return TimetableService(db).student_timetable(user, semester_id, week)


@router.get(
    "/lecturers/me/timetable", response_model=Timetable, summary="Lịch dạy giảng viên (UC008)"
)
def lecturer_timetable(
    user: LecturerUser,
    db: DbSession,
    semester_id: int | None = Query(None, alias="semesterId"),
    week: int | None = Query(None, ge=1),
):
    if semester_id is None:
        semester_id = SemesterService(db).get_current().id
    return TimetableService(db).lecturer_timetable(user, semester_id, week)


@router.get(
    "/lecturers/me/sections", response_model=ItemList[Section], summary="Các lớp được phân công"
)
def lecturer_sections(
    user: LecturerUser, db: DbSession, semester_id: int | None = Query(None, alias="semesterId")
):
    if semester_id is None:
        semester_id = SemesterService(db).get_current().id
    return TimetableService(db).lecturer_sections(user, semester_id)


@router.post(
    "/timetable/check",
    summary="Kiểm tra xung đột thời khóa biểu (không ghi DB)",
)
def timetable_check(
    user: AdminUser,
    slots: list[ScheduleSlot] = Body(...),
) -> list[ScheduleConflict]:
    from app.service.timetable.conflict_engine import find_conflicts

    return [ScheduleConflict.model_validate(item) for item in find_conflicts(slots)]


@router.post(
    "/students/me/timetable/suggestions",
    summary="Đề xuất lịch học cho sinh viên",
)
def student_timetable_suggestions(
    user: StudentUser,
    db: DbSession,
    payload: dict | list[dict] | None = Body(default=None),
):
    from app.service.timetable.conflict_engine import find_conflicts, suggest_timetables

    if isinstance(payload, list):
        return {"items": suggest_timetables(payload)}

    payload_dict: dict[str, Any] = payload or {}
    avoid_early = payload_dict.get("avoidEarly") or payload_dict.get("avoid_early")
    avoid_late = payload_dict.get("avoidLate") or payload_dict.get("avoid_late")
    blocked_days = payload_dict.get("blockedDays") or payload_dict.get("blocked_days")
    max_results = int(payload_dict.get("maxResults") or payload_dict.get("max_results") or 5)
    subject_ids = payload_dict.get("subjectIds") or payload_dict.get("subject_ids")

    if subject_ids:
        cur_semester = SemesterService(db).get_current()
        stmt = (
            select(CourseSection)
            .options(
                joinedload(CourseSection.subject),
                joinedload(CourseSection.room),
                joinedload(CourseSection.lecturer),
            )
            .where(
                CourseSection.semester_id == cur_semester.id,
                CourseSection.subject_id.in_(subject_ids),
                CourseSection.current_enrollment < CourseSection.max_capacity,
            )
        )
        sections = list(db.scalars(stmt).unique().all())
        by_subject: dict[int, list[CourseSection]] = {}
        for s in sections:
            by_subject.setdefault(s.subject_id, []).append(s)

        subject_lists = [by_subject[sid] for sid in subject_ids if sid in by_subject]
        suggestions: list[dict[str, Any]] = []
        if subject_lists:
            for combo in product(*subject_lists):
                if blocked_days and any(s.day_of_week in blocked_days for s in combo):
                    continue
                if avoid_early is not None and any(s.start_period < avoid_early for s in combo):
                    continue
                if avoid_late is not None and any(s.end_period > avoid_late for s in combo):
                    continue
                if find_conflicts(combo):
                    continue
                suggestions.append(
                    {
                        "sections": [
                            {
                                "id": s.id,
                                "sectionCode": s.section_code,
                                "subjectId": s.subject_id,
                                "subjectName": s.subject.name if s.subject else "",
                                "subjectCode": s.subject.subject_code if s.subject else "",
                                "credits": s.subject.credits if s.subject else 0,
                                "dayOfWeek": s.day_of_week,
                                "startPeriod": s.start_period,
                                "endPeriod": s.end_period,
                                "startWeek": s.start_week,
                                "endWeek": s.end_week,
                                "roomCode": s.room.room_code if s.room else "",
                                "lecturerName": s.lecturer.full_name if s.lecturer else "",
                            }
                            for s in combo
                        ]
                    }
                )
                if len(suggestions) >= max_results:
                    break
        return {"items": suggestions}

    raw_sections = (
        payload_dict.get("sections") or payload_dict.get("items") or payload_dict.get("slots") or []
    )
    return {
        "items": suggest_timetables(
            raw_sections,
            avoid_early=avoid_early,
            avoid_late=avoid_late,
            blocked_days=blocked_days,
            max_results=max_results,
        )
    }
