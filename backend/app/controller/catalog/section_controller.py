from fastapi import APIRouter, Query, Response, status

from app.controller.pagination import Pagination
from app.core.database import DbSession
from app.dto.catalog.catalog import (
    Lookups,
    Section,
    SectionCreateRequest,
    SectionStudentList,
    SectionUpdateRequest,
)
from app.dto.common import Page
from app.security.dependencies import AdminOrLecturer, AdminOrStudent, AdminUser
from app.service.catalog.section_service import SectionService
from app.service.catalog.semester_service import SemesterService

router = APIRouter(prefix="/sections", tags=["catalog"])


@router.get("", response_model=Page[Section], summary="Danh sách lớp học phần")
def list_sections(
    user: AdminOrStudent,
    db: DbSession,
    paging: Pagination,
    semester_id: int | None = Query(None, alias="semesterId"),
    subject_id: int | None = Query(None, alias="subjectId"),
    keyword: str | None = None,
    unit_keyword: str | None = Query(None, alias="unitKeyword"),
):
    if semester_id is None:
        semester_id = SemesterService(db).get_current().id
    return SectionService(db).list(user, semester_id, subject_id, keyword, unit_keyword, paging)


# /lookups phải đứng TRƯỚC /{section_id}
@router.get("/lookups", response_model=Lookups, summary="Dữ liệu cho form lớp học phần")
def get_lookups(_admin: AdminUser, db: DbSession):
    return SectionService(db).get_lookups()


@router.get("/{section_id}", response_model=Section, summary="Chi tiết lớp học phần")
def get_section(section_id: int, _admin: AdminUser, db: DbSession):
    return SectionService(db).get(section_id)


@router.post(
    "", response_model=Section, status_code=status.HTTP_201_CREATED, summary="Thêm lớp học phần"
)
def create_section(body: SectionCreateRequest, _admin: AdminUser, db: DbSession):
    return SectionService(db).create(body)


@router.put("/{section_id}", response_model=Section, summary="Sửa lớp học phần")
def update_section(section_id: int, body: SectionUpdateRequest, _admin: AdminUser, db: DbSession):
    return SectionService(db).update(section_id, body)


@router.delete(
    "/{section_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Xóa lớp học phần",
)
def delete_section(section_id: int, _admin: AdminUser, db: DbSession):
    SectionService(db).delete(section_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{section_id}/students",
    response_model=SectionStudentList,
    summary="Danh sách sinh viên của lớp (UC003, UC009)",
)
def list_section_students(section_id: int, user: AdminOrLecturer, db: DbSession):
    return SectionService(db).list_students(user, section_id)
