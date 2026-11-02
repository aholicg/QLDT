from fastapi import APIRouter, Query, Response, status

from app.core.database import DbSession
from app.dto.common import ItemList
from app.dto.registration.registration import (
    ChangeSectionRequest,
    RegisterRequest,
    Registration,
)
from app.security.dependencies import StudentUser
from app.service.catalog.semester_service import SemesterService
from app.service.registration.registration_service import RegistrationService

router = APIRouter(prefix="/registrations", tags=["registration"])


@router.post(
    "",
    response_model=Registration,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký lớp học phần (UC005)",
)
def register(body: RegisterRequest, user: StudentUser, db: DbSession):
    return RegistrationService(db).register(user, body)


# /me phải đứng TRƯỚC /{registration_id}
@router.get("/me", response_model=ItemList[Registration], summary="Các lớp đã đăng ký của tôi")
def my_registrations(
    user: StudentUser, db: DbSession, semester_id: int | None = Query(None, alias="semesterId")
):
    if semester_id is None:
        semester_id = SemesterService(db).get_current().id
    return RegistrationService(db).list_mine(user, semester_id)


@router.delete(
    "/{registration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Hủy đăng ký (UC006)",
)
def cancel(registration_id: int, user: StudentUser, db: DbSession):
    RegistrationService(db).cancel(user, registration_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{registration_id}/change",
    response_model=Registration,
    summary="Đổi lớp học phần (UC006 - Atomic Change)",
)
def change_section(
    registration_id: int, body: ChangeSectionRequest, user: StudentUser, db: DbSession
):
    return RegistrationService(db).change_section(user, registration_id, body)
