from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError, field_error
from app.dto.common import ItemList
from app.dto.registration.registration import RegisterRequest
from app.dto.registration.registration import Registration as RegistrationDto
from app.entity.auth.user import User
from app.entity.registration.registration import Registration as RegistrationEntity
from app.repository.auth.user_repository import StudentRepository
from app.repository.catalog.section_repository import SectionRepository
from app.repository.registration.registration_repository import RegistrationRepository


class RegistrationService:
    """UC005 (đăng ký) và UC006 (hủy). Mỗi thao tác ghi là MỘT giao dịch: db.commit() ở cuối,
    lỗi nghiệp vụ -> ném AppError (get_db sẽ rollback)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.students = StudentRepository(db)
        self.sections = SectionRepository(db)
        self.registrations = RegistrationRepository(db)

    def _sync_tuition_invoice_after_change(self, student_id: int, semester_id: int) -> None:
        from app.repository.catalog.semester_repository import SemesterRepository
        from app.repository.tuition.tuition_repository import TuitionRepository

        tuition_repo = TuitionRepository(self.db)
        inv = tuition_repo.get_invoice_by_student_semester_for_update(student_id, semester_id)
        if inv is not None:
            if inv.amount_paid == 0:
                rates = tuition_repo.list_rates(semester_id)
                if rates:
                    from app.service.tuition.tuition_service import TuitionService

                    student = self.students.get_by_id(student_id)
                    semester = SemesterRepository(self.db).get_by_id(semester_id)
                    subj_map = tuition_repo.get_registered_students_and_subjects(
                        semester_id, student_id
                    )
                    subjects = subj_map.get(student_id, [])
                    if student and semester:
                        TuitionService(self.db).generate_single_invoice(
                            student, semester, rates, subjects
                        )
            else:
                inv.is_stale = True

    def register(self, user: User, request: RegisterRequest) -> RegistrationDto:
        student = self.students.get_by_user_id_for_update(user.id)
        if student is None:
            raise AppError(ErrorCode.FORBIDDEN)

        section = self.sections.get_by_id(request.section_id)
        if section is None:
            raise AppError(
                ErrorCode.NOT_FOUND,
                details=[field_error("sectionId", "Lớp học phần không tồn tại")],
            )

        if self.registrations.exists(student.id, section.id):
            raise AppError(ErrorCode.ALREADY_REGISTERED)
        if self.registrations.find_same_subject(
            student.id, section.subject_id, section.semester_id
        ):
            raise AppError(ErrorCode.SAME_SUBJECT_REGISTERED)

        conflicts = self.registrations.find_schedule_conflicts(student.id, section)
        if conflicts:
            raise AppError(
                ErrorCode.STUDENT_SCHEDULE_CONFLICT,
                details=[
                    field_error("sectionCode", f"Lớp {conflict.section_code} bị trùng lịch")
                    for conflict in conflicts
                ],
            )

        current_credits = self.registrations.total_credits(student.id, section.semester_id)
        if current_credits + section.subject.credits > settings.max_credits_per_semester:
            raise AppError(
                ErrorCode.CREDIT_LIMIT_EXCEEDED,
                details=[
                    field_error("currentCredits", f"Số tín chỉ hiện tại: {current_credits}"),
                    field_error(
                        "maxCredits",
                        f"Mức tối đa: {settings.max_credits_per_semester} tín chỉ",
                    ),
                ],
            )

        if not self.sections.increment_enrollment_if_available(section.id):
            raise AppError(ErrorCode.CLASS_FULL)

        registration = self.registrations.add(
            RegistrationEntity(student_id=student.id, section_id=section.id)
        )
        self._sync_tuition_invoice_after_change(student.id, section.semester_id)
        self.db.commit()
        loaded_registration = self.registrations.get_by_id(registration.id)
        result = RegistrationDto.model_validate(loaded_registration)
        result.section.registered_by_me = True
        return result

    def cancel(self, user: User, registration_id: int) -> None:
        student = self.students.get_by_user_id_for_update(user.id)
        if student is None:
            raise AppError(ErrorCode.FORBIDDEN)

        registration = self.registrations.get_by_id(registration_id)
        if registration is None:
            raise AppError(ErrorCode.NOT_FOUND)
        if registration.student_id != student.id:
            raise AppError(ErrorCode.FORBIDDEN)

        section = registration.section
        if section is None:
            raise AppError(ErrorCode.NOT_FOUND)

        current_credits = self.registrations.total_credits(student.id, section.semester_id)
        if False and (
            current_credits >= settings.min_credits_per_semester
            and current_credits - section.subject.credits < settings.min_credits_per_semester
        ):
            raise AppError(
                ErrorCode.CREDIT_LIMIT_BELOW_MIN,
                details=[
                    field_error("currentCredits", f"Số tín chỉ hiện tại: {current_credits}"),
                    field_error(
                        "minCredits",
                        f"Mức tối thiểu: {settings.min_credits_per_semester} tín chỉ",
                    ),
                ],
            )

        self.registrations.delete(registration)
        self.sections.decrement_enrollment(section.id)
        self._sync_tuition_invoice_after_change(student.id, section.semester_id)
        self.db.commit()

    def list_mine(self, user: User, semester_id: int) -> ItemList[RegistrationDto]:
        student = self.students.get_by_user_id(user.id)
        if student is None:
            return ItemList[RegistrationDto](items=[])

        registrations = self.registrations.list_by_student(student.id, semester_id)
        items: list[RegistrationDto] = []
        for registration in registrations:
            dto = RegistrationDto.model_validate(registration)
            dto.section.registered_by_me = True
            items.append(dto)
        return ItemList[RegistrationDto](items=items)
