from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.database import DbSession
from app.dto.common import ItemList
from app.dto.registration.academic_records import (
    AttendanceSheet,
    AttendanceUpdateRequest,
    GradeBook,
    GradeComponent,
    GradeComponentsRequest,
    GradeUpdateRequest,
)
from app.security.dependencies import AdminUser, LecturerUser
from app.service.registration.academic_records_service import AcademicRecordsService

router = APIRouter(prefix="/sections", tags=["academic-records"])


@router.get("/{section_id}/attendance", response_model=AttendanceSheet)
def get_attendance(
    section_id: int,
    user: LecturerUser,
    db: DbSession,
    class_date: date | None = Query(None, alias="classDate"),
):
    return AcademicRecordsService(db).attendance_sheet(user, section_id, class_date)


@router.put("/{section_id}/attendance", response_model=AttendanceSheet)
def save_attendance(
    section_id: int,
    body: AttendanceUpdateRequest,
    user: LecturerUser,
    db: DbSession,
):
    return AcademicRecordsService(db).save_attendance(user, section_id, body)


@router.get("/{section_id}/grades", response_model=GradeBook)
def get_gradebook(section_id: int, user: LecturerUser, db: DbSession):
    return AcademicRecordsService(db).gradebook(user, section_id)


@router.get("/{section_id}/grade-components", response_model=ItemList[GradeComponent])
def get_grade_components(section_id: int, _admin: AdminUser, db: DbSession):
    return {"items": AcademicRecordsService(db).get_grade_components(section_id)}


@router.put("/{section_id}/grades", response_model=GradeBook)
def save_grades(
    section_id: int,
    body: GradeUpdateRequest,
    user: LecturerUser,
    db: DbSession,
):
    return AcademicRecordsService(db).save_grades(user, section_id, body)


@router.put("/{section_id}/grade-components", response_model=ItemList[GradeComponent])
def configure_grade_components(
    section_id: int,
    body: GradeComponentsRequest,
    _admin: AdminUser,
    db: DbSession,
):
    return {"items": AcademicRecordsService(db).configure_grade_components(section_id, body)}


@router.get(
    "/{section_id}/exports/attendance",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                    "schema": {"type": "string", "format": "binary"}
                }
            }
        }
    },
)
def export_attendance(section_id: int, user: LecturerUser, db: DbSession):
    output = AcademicRecordsService(db).export_attendance(user, section_id)
    filename = quote(f"diem-danh-lop-{section_id}.xlsx")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.get(
    "/{section_id}/exports/grades",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                    "schema": {"type": "string", "format": "binary"}
                }
            }
        }
    },
)
def export_grades(section_id: int, user: LecturerUser, db: DbSession):
    output = AcademicRecordsService(db).export_gradebook(user, section_id)
    filename = quote(f"bang-diem-lop-{section_id}.xlsx")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
