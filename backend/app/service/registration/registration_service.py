from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError, field_error
from app.dto.common import ItemList
from app.dto.registration.registration import ChangeSectionRequest, RegisterRequest
from app.dto.registration.registration import Registration as RegistrationDto
from app.entity.auth.user import User
from app.entity.registration.registration import Registration as RegistrationEntity
from app.repository.auth.user_repository import StudentRepository
from app.repository.catalog.section_repository import SectionRepository
from app.repository.registration.registration_repository import RegistrationRepository


class RegistrationService:
    """UC005 (đăng ký), UC006 (hủy & đổi lớp). Mỗi thao tác ghi là MỘT giao dịch: db.commit() ở cuối,
    lỗi nghiệp vụ -> ném AppError (get_db sẽ rollback)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.students = StudentRepository(db)
        self.sections = SectionRepository(db)
        self.registrations = RegistrationRepository(db)

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
        if (
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
        self.db.commit()

    def change_section(
        self, user: User, registration_id: int, request: ChangeSectionRequest
    ) -> RegistrationDto:
        """Đổi lớp học phần nguyên tử (Atomic Change Section - UC006).

        Cho phép đổi sang lớp khác của cùng môn học mà không bị rủi ro mất chỗ lớp cũ
        nếu lớp mới bị đầy hoặc bị trùng lịch.
        """
        student = self.students.get_by_user_id_for_update(user.id)
        if student is None:
            raise AppError(ErrorCode.FORBIDDEN)

        old_registration = self.registrations.get_by_id(registration_id)
        if old_registration is None:
            raise AppError(ErrorCode.NOT_FOUND)
        if old_registration.student_id != student.id:
            raise AppError(ErrorCode.FORBIDDEN)

        old_section = old_registration.section
        if old_section is None:
            raise AppError(ErrorCode.NOT_FOUND)

        if old_section.id == request.new_section_id:
            # Đang ở đúng lớp này rồi, trả về luôn
            result = RegistrationDto.model_validate(old_registration)
            result.section.registered_by_me = True
            return result

        new_section = self.sections.get_by_id(request.new_section_id)
        if new_section is None:
            raise AppError(
                ErrorCode.NOT_FOUND,
                details=[field_error("newSectionId", "Lớp học phần mới không tồn tại")],
            )

        if new_section.subject_id != old_section.subject_id:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                details=[
                    field_error(
                        "newSectionId", "Chỉ được đổi sang lớp học phần của cùng một môn học"
                    )
                ],
            )

        if new_section.semester_id != old_section.semester_id:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                details=[
                    field_error("newSectionId", "Lớp mới phải thuộc cùng học kỳ với lớp hiện tại")
                ],
            )

        # Kiểm tra trùng lịch với các lớp khác (ngoại trừ lớp cũ đang muốn đổi)
        conflicts = [
            c
            for c in self.registrations.find_schedule_conflicts(student.id, new_section)
            if c.id != old_section.id
        ]
        if conflicts:
            raise AppError(
                ErrorCode.STUDENT_SCHEDULE_CONFLICT,
                details=[
                    field_error("sectionCode", f"Lớp {conflict.section_code} bị trùng lịch")
                    for conflict in conflicts
                ],
            )

        # Tăng sĩ số lớp mới (atomic)
        if not self.sections.increment_enrollment_if_available(new_section.id):
            raise AppError(ErrorCode.CLASS_FULL)

        # Giảm sĩ số lớp cũ và cập nhật bản ghi đăng ký
        self.sections.decrement_enrollment(old_section.id)
        old_registration.section_id = new_section.id
        self.db.commit()
        self.db.expire_all()

        loaded_registration = self.registrations.get_by_id(old_registration.id)
        result = RegistrationDto.model_validate(loaded_registration)
        result.section.registered_by_me = True
        return result

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
