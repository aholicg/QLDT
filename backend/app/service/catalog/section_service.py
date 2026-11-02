from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError, field_error
from app.core.timeutil import to_vn
from app.dto.catalog.catalog import (
    LecturerRef,
    Lookups,
    RoomRef,
    Section,
    SectionCreateRequest,
    SectionStudent,
    SectionStudentList,
    SectionUpdateRequest,
    SubjectRef,
)
from app.dto.catalog.catalog import (
    Semester as SemesterDto,
)
from app.dto.common import Page, PageParams
from app.entity.auth.student import Student
from app.entity.auth.user import Role, User
from app.entity.catalog.course_section import CourseSection
from app.entity.registration.registration import Registration
from app.repository.auth.user_repository import LecturerRepository, StudentRepository
from app.repository.catalog.lookup_repository import LookupRepository
from app.repository.catalog.section_repository import SectionRepository
from app.repository.catalog.semester_repository import SemesterRepository
from app.repository.catalog.subject_repository import SubjectRepository
from app.repository.registration.registration_repository import RegistrationRepository


class SectionService:
    """UC002 (CRUD lớp học phần), UC003 và UC009 (danh sách sinh viên của lớp)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.sections = SectionRepository(db)
        self.registrations = RegistrationRepository(db)
        self.lookups = LookupRepository(db)
        self.subjects = SubjectRepository(db)
        self.semesters = SemesterRepository(db)
        self.lecturers = LecturerRepository(db)
        self.students = StudentRepository(db)

    def list(
        self,
        user: User,
        semester_id: int,
        subject_id: int | None,
        keyword: str | None,
        unit_keyword: str | None,
        paging: PageParams,
    ) -> Page[Section]:
        items, total = self.sections.search(
            semester_id=semester_id,
            subject_id=subject_id,
            keyword=keyword,
            unit_keyword=unit_keyword,
            offset=paging.offset,
            limit=paging.size,
            sort=paging.sort,
        )

        registered_ids: set[int] = set()
        if user.role == Role.STUDENT:
            student = self.students.get_by_user_id(user.id)
            if student:
                registered_ids = self.registrations.registered_section_ids_for_student(
                    student.id, semester_id
                )

        dtos: list[Section] = []
        for s in items:
            dto = Section.model_validate(s)
            if user.role == Role.STUDENT:
                dto.registered_by_me = s.id in registered_ids
            else:
                dto.registered_by_me = None
            dtos.append(dto)

        return Page.of(dtos, paging, total)

    def get(self, section_id: int) -> Section:
        entity = self.sections.get_by_id(section_id)
        if entity is None:
            raise AppError(ErrorCode.NOT_FOUND)
        return Section.model_validate(entity)

    def get_lookups(self) -> Lookups:
        subjects = [SubjectRef.model_validate(s) for s in self.lookups.list_subjects()]
        lecturers = [
            LecturerRef(id=lec.id, lecturer_code=lec.lecturer_code, full_name=lec.full_name)
            for lec in self.lookups.list_lecturers()
        ]
        rooms = [RoomRef.model_validate(r) for r in self.lookups.list_rooms()]
        semesters = [SemesterDto.model_validate(s) for s in self.semesters.list_all()]
        return Lookups(subjects=subjects, lecturers=lecturers, rooms=rooms, semesters=semesters)

    def create(self, request: SectionCreateRequest) -> Section:
        subject = self.subjects.get_by_id(request.subject_id)
        if subject is None:
            raise AppError(
                ErrorCode.NOT_FOUND, details=[field_error("subjectId", "Môn học không tồn tại")]
            )

        semester = self.semesters.get_by_id(request.semester_id)
        if semester is None:
            raise AppError(
                ErrorCode.NOT_FOUND, details=[field_error("semesterId", "Học kỳ không tồn tại")]
            )

        lecturer = self.lecturers.get_by_id(request.lecturer_id)
        if lecturer is None:
            raise AppError(
                ErrorCode.NOT_FOUND, details=[field_error("lecturerId", "Giảng viên không tồn tại")]
            )

        room = self.lookups.get_room_by_id(request.room_id)
        if room is None:
            raise AppError(
                ErrorCode.NOT_FOUND, details=[field_error("roomId", "Phòng học không tồn tại")]
            )

        if self.sections.exists_by_code(request.section_code):
            raise AppError(
                ErrorCode.DUPLICATE_CODE,
                details=[field_error("sectionCode", "Mã lớp học phần đã tồn tại")],
            )

        if request.end_week > semester.num_weeks:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                details=[
                    field_error(
                        "endWeek",
                        f"Tuần kết thúc không được vượt quá số tuần của học kỳ ({semester.num_weeks})",
                    )
                ],
            )

        if request.max_capacity > room.capacity:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                details=[
                    field_error(
                        "maxCapacity",
                        f"Sĩ số tối đa ({request.max_capacity}) vượt quá sức chứa phòng ({room.capacity})",
                    )
                ],
            )

        self.db.execute(
            select(lecturer.__class__).where(lecturer.__class__.id == lecturer.id).with_for_update()
        )
        self.db.execute(
            select(room.__class__).where(room.__class__.id == room.id).with_for_update()
        )

        conflicts = self.sections.find_room_or_lecturer_conflict_details(
            semester_id=request.semester_id,
            room_id=request.room_id,
            lecturer_id=request.lecturer_id,
            day_of_week=request.day_of_week,
            start_period=request.start_period,
            end_period=request.end_period,
            start_week=request.start_week,
            end_week=request.end_week,
            target_section_code=request.section_code,
        )
        if conflicts:
            conflict_details = [
                {
                    **detail,
                    "field": "roomId" if detail["type"] == "ROOM" else "lecturerId",
                }
                for _, detail in conflicts
            ]
            raise AppError(ErrorCode.SCHEDULE_CONFLICT, details=conflict_details)

        entity = CourseSection(
            section_code=request.section_code,
            subject_id=request.subject_id,
            semester_id=request.semester_id,
            lecturer_id=request.lecturer_id,
            room_id=request.room_id,
            day_of_week=request.day_of_week,
            start_period=request.start_period,
            end_period=request.end_period,
            start_week=request.start_week,
            end_week=request.end_week,
            max_capacity=request.max_capacity,
            current_enrollment=0,
        )
        self.sections.add(entity)
        self.db.commit()
        loaded = self.sections.get_by_id(entity.id)
        return Section.model_validate(loaded)

    def update(self, section_id: int, request: SectionUpdateRequest) -> Section:
        entity = self.sections.get_by_id(section_id)
        if entity is None:
            raise AppError(ErrorCode.NOT_FOUND)

        semester = self.semesters.get_by_id(request.semester_id)
        if semester is None:
            raise AppError(
                ErrorCode.NOT_FOUND, details=[field_error("semesterId", "Học kỳ không tồn tại")]
            )

        subject = self.subjects.get_by_id(request.subject_id)
        if subject is None:
            raise AppError(
                ErrorCode.NOT_FOUND, details=[field_error("subjectId", "Môn học không tồn tại")]
            )

        lecturer = self.lecturers.get_by_id(request.lecturer_id)
        if lecturer is None:
            raise AppError(
                ErrorCode.NOT_FOUND, details=[field_error("lecturerId", "Giảng viên không tồn tại")]
            )

        room = self.lookups.get_room_by_id(request.room_id)
        if room is None:
            raise AppError(
                ErrorCode.NOT_FOUND, details=[field_error("roomId", "Phòng học không tồn tại")]
            )

        if request.end_week > semester.num_weeks:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                details=[
                    field_error(
                        "endWeek",
                        f"Tuần kết thúc không được vượt quá số tuần của học kỳ ({semester.num_weeks})",
                    )
                ],
            )

        if request.max_capacity > room.capacity:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                details=[
                    field_error(
                        "maxCapacity",
                        f"Sĩ số tối đa ({request.max_capacity}) vượt quá sức chứa phòng ({room.capacity})",
                    )
                ],
            )

        if request.max_capacity < entity.current_enrollment:
            raise AppError(
                ErrorCode.CAPACITY_BELOW_ENROLLMENT,
                details=[
                    field_error(
                        "maxCapacity",
                        f"Sĩ số tối đa không được nhỏ hơn số sinh viên đã đăng ký ({entity.current_enrollment})",
                    )
                ],
            )

        if entity.current_enrollment > 0:
            if request.subject_id != entity.subject_id or request.semester_id != entity.semester_id:
                raise AppError(
                    ErrorCode.SECTION_HAS_REGISTRATIONS,
                    message="Lớp học phần đã có sinh viên đăng ký, không thể đổi môn học hoặc học kỳ",
                )

        self.db.execute(
            select(lecturer.__class__).where(lecturer.__class__.id == lecturer.id).with_for_update()
        )
        self.db.execute(
            select(room.__class__).where(room.__class__.id == room.id).with_for_update()
        )

        conflicts = self.sections.find_room_or_lecturer_conflict_details(
            semester_id=request.semester_id,
            room_id=request.room_id,
            lecturer_id=request.lecturer_id,
            day_of_week=request.day_of_week,
            start_period=request.start_period,
            end_period=request.end_period,
            start_week=request.start_week,
            end_week=request.end_week,
            target_section_code=entity.section_code,
            exclude_section_id=section_id,
        )
        if conflicts:
            conflict_details = [
                {
                    **detail,
                    "field": "roomId" if detail["type"] == "ROOM" else "lecturerId",
                }
                for _, detail in conflicts
            ]
            raise AppError(ErrorCode.SCHEDULE_CONFLICT, details=conflict_details)

        schedule_changed = (
            request.day_of_week != entity.day_of_week
            or request.start_period != entity.start_period
            or request.end_period != entity.end_period
            or request.start_week != entity.start_week
            or request.end_week != entity.end_week
        )
        if schedule_changed and self.sections.count_registrations(section_id) > 0:
            from app.service.timetable.conflict_engine import find_conflicts

            stmt = (
                select(Student.student_code, CourseSection)
                .join(Registration, Registration.section_id == CourseSection.id)
                .join(Student, Registration.student_id == Student.id)
                .where(
                    Registration.student_id.in_(
                        select(Registration.student_id).where(Registration.section_id == entity.id)
                    ),
                    CourseSection.semester_id == request.semester_id,
                    CourseSection.id != entity.id,
                    CourseSection.day_of_week == request.day_of_week,
                )
            )
            other_rows = self.db.execute(stmt).all()
            if other_rows:
                target_slot = {
                    "sectionCode": entity.section_code,
                    "dayOfWeek": request.day_of_week,
                    "startPeriod": request.start_period,
                    "endPeriod": request.end_period,
                    "startWeek": request.start_week,
                    "endWeek": request.end_week,
                }
                student_conflict_details = []
                for student_code, other_section in other_rows:
                    slot_conflicts = find_conflicts([target_slot, other_section])
                    if slot_conflicts:
                        student_conflict_details.extend(
                            {
                                **conflict,
                                "field": "schedule",
                                "studentCode": student_code,
                                "message": (
                                    f"[STUDENT] Sinh viên {student_code} bị trùng lịch giữa lớp "
                                    f"{entity.section_code} và {other_section.section_code}"
                                ),
                                "type": "STUDENT",
                            }
                            for conflict in slot_conflicts
                        )
                if student_conflict_details:
                    raise AppError(ErrorCode.SCHEDULE_CONFLICT, details=student_conflict_details)

        # Gán cả quan hệ (không chỉ FK id) để object trả về không bị cũ
        # (stale) khi session không tự expire/refresh sau khi đổi FK.
        entity.subject = subject
        entity.semester = semester
        entity.lecturer = lecturer
        entity.room = room
        entity.day_of_week = request.day_of_week
        entity.start_period = request.start_period
        entity.end_period = request.end_period
        entity.start_week = request.start_week
        entity.end_week = request.end_week
        entity.max_capacity = request.max_capacity

        self.db.commit()
        # Ép nạp lại từ DB trước khi serialize để chắc chắn dữ liệu mới.
        self.db.expire(entity)
        loaded = self.sections.get_by_id(entity.id)
        return Section.model_validate(loaded)

    def delete(self, section_id: int) -> None:
        entity = self.sections.get_by_id(section_id)
        if entity is None:
            raise AppError(ErrorCode.NOT_FOUND)

        if self.sections.count_registrations(section_id) > 0:
            raise AppError(ErrorCode.SECTION_HAS_REGISTRATIONS)

        self.sections.delete(entity)
        self.db.commit()

    def list_students(self, user: User, section_id: int) -> SectionStudentList:
        entity = self.sections.get_by_id(section_id)
        if entity is None:
            raise AppError(ErrorCode.NOT_FOUND)

        if user.role == Role.LECTURER:
            lecturer = self.lecturers.get_by_user_id(user.id)
            if lecturer is None or entity.lecturer_id != lecturer.id:
                raise AppError(ErrorCode.FORBIDDEN)

        registrations = self.registrations.list_students_of_section(section_id)
        items: list[SectionStudent] = []
        for r in registrations:
            items.append(
                SectionStudent(
                    id=r.student.id,
                    student_code=r.student.student_code,
                    full_name=r.student.full_name,
                    email=r.student.email,
                    cohort=r.student.cohort,
                    major=r.student.major,
                    registered_at=to_vn(r.registered_at),
                )
            )

        return SectionStudentList(
            section_id=entity.id,
            section_code=entity.section_code,
            current_enrollment=entity.current_enrollment,
            max_capacity=entity.max_capacity,
            items=items,
        )
