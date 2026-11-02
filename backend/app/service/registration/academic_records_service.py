from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy.orm import Session

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError, field_error
from app.core.timeutil import today_vn
from app.dto.registration.academic_records import (
    AttendanceEntry,
    AttendanceSheet,
    AttendanceUpdateRequest,
    GradeBook,
    GradeComponent,
    GradeComponentsRequest,
    GradeUpdateRequest,
    StudentGradeRow,
    round_final_score,
)
from app.entity.auth.user import User
from app.entity.catalog.course_section import CourseSection
from app.entity.registration.attendance import (
    AttendanceStatus as AttendanceStatusEntity,
)
from app.entity.registration.attendance import (
    GradeComponent as GradeComponentEntity,
)
from app.repository.auth.user_repository import LecturerRepository
from app.repository.catalog.section_repository import SectionRepository
from app.repository.registration.academic_records_repository import AcademicRecordsRepository


class AcademicRecordsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.sections = SectionRepository(db)
        self.records = AcademicRecordsRepository(db)
        self.lecturers = LecturerRepository(db)

    def _section(self, user: User, section_id: int) -> CourseSection:
        section = self.sections.get_by_id(section_id)
        if section is None:
            raise AppError(ErrorCode.NOT_FOUND)
        lecturer = self.lecturers.get_by_user_id(user.id)
        if lecturer is None or section.lecturer_id != lecturer.id:
            raise AppError(ErrorCode.FORBIDDEN)
        return section

    @staticmethod
    def _validate_class_date(section: CourseSection, class_date: date) -> None:
        first_date = section.semester.start_date + timedelta(days=section.day_of_week - 2)
        offset = (class_date - first_date).days
        week_index = offset // 7 + 1
        if (
            offset < 0
            or offset % 7 != 0
            or week_index < section.start_week
            or week_index > section.end_week
        ):
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                details=[
                    field_error(
                        "classDate",
                        "Ngày điểm danh không thuộc lịch học của lớp học phần",
                    )
                ],
            )

    def attendance_sheet(
        self, user: User, section_id: int, class_date: date | None
    ) -> AttendanceSheet:
        section = self._section(user, section_id)
        scheduled_dates = self._class_dates(section)
        if class_date is None:
            class_date = next(
                (
                    scheduled_date
                    for scheduled_date in scheduled_dates
                    if scheduled_date >= today_vn()
                ),
                scheduled_dates[-1],
            )
        self._validate_class_date(section, class_date)
        registrations = self.records.list_roster(section_id)
        attendance = self.records.attendance_for_date(section_id, class_date)
        return AttendanceSheet(
            section_id=section.id,
            section_code=section.section_code,
            class_date=class_date,
            scheduled_dates=scheduled_dates,
            items=[
                AttendanceEntry(
                    student_id=registration.student.id,
                    student_code=registration.student.student_code,
                    full_name=registration.student.full_name,
                    email=registration.student.user.email,
                    status=attendance[registration.student.id].status
                    if registration.student.id in attendance
                    else None,
                )
                for registration in registrations
            ],
        )

    def save_attendance(
        self, user: User, section_id: int, request: AttendanceUpdateRequest
    ) -> AttendanceSheet:
        section = self._section(user, section_id)
        self._validate_class_date(section, request.class_date)
        registrations = self.records.list_roster(section_id)
        roster_ids = {registration.student.id for registration in registrations}
        submitted_ids = [item.student_id for item in request.items]
        if len(set(submitted_ids)) != len(submitted_ids) or set(submitted_ids) != roster_ids:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                details=[
                    field_error(
                        "items",
                        "Cần gửi trạng thái đúng một lần cho từng sinh viên đang đăng ký lớp",
                    )
                ],
            )
        for item in request.items:
            self.records.save_attendance(
                section_id=section.id,
                student_id=item.student_id,
                class_date=request.class_date,
                status=AttendanceStatusEntity(item.status.value),
                marked_by_user_id=user.id,
            )
        self.db.commit()
        return self.attendance_sheet(user, section_id, request.class_date)

    def configure_grade_components(
        self, section_id: int, request: GradeComponentsRequest
    ) -> list[GradeComponent]:
        section = self.sections.get_by_id(section_id)
        if section is None:
            raise AppError(ErrorCode.NOT_FOUND)
        current = self.records.list_components(section_id)
        if self.records.has_grade_scores([component.id for component in current]):
            raise AppError(
                ErrorCode.GRADE_COMPONENTS_LOCKED,
                details=[
                    field_error(
                        "items",
                        "Không thể đổi cấu trúc điểm sau khi đã nhập điểm cho sinh viên",
                    )
                ],
            )
        self.records.delete_components(current)
        self.records.add_components(
            [
                GradeComponentEntity(
                    section_id=section_id,
                    name=item.name.strip(),
                    weight_percentage=item.weight_percentage,
                    max_score=item.max_score,
                    sort_order=index,
                )
                for index, item in enumerate(request.items)
            ]
        )
        self.db.commit()
        return [
            GradeComponent.model_validate(component)
            for component in self.records.list_components(section_id)
        ]

    def get_grade_components(self, section_id: int) -> list[GradeComponent]:
        if self.sections.get_by_id(section_id) is None:
            raise AppError(ErrorCode.NOT_FOUND)
        return [
            GradeComponent.model_validate(component)
            for component in self.records.list_components(section_id)
        ]

    def gradebook(self, user: User, section_id: int) -> GradeBook:
        section = self._section(user, section_id)
        registrations = self.records.list_roster(section_id)
        components = self.records.list_components(section_id)
        component_ids = [component.id for component in components]
        grades = self.records.grade_scores(component_ids)
        scores_by_student: dict[int, dict[int, Decimal]] = {}
        for grade in grades:
            scores_by_student.setdefault(grade.student_id, {})[grade.component_id] = Decimal(
                str(grade.score)
            )
        component_dtos = [GradeComponent.model_validate(component) for component in components]
        rows: list[StudentGradeRow] = []
        for registration in registrations:
            student = registration.student
            scores = scores_by_student.get(student.id, {})
            decimal_scores = {
                component_id: scores.get(component_id) for component_id in component_ids
            }
            final_score: Decimal | None = None
            if component_ids and all(
                decimal_scores[component_id] is not None for component_id in component_ids
            ):
                weighted_score = sum(
                    (
                        decimal_scores[component.id]
                        / Decimal(str(component.max_score))
                        * Decimal("10")
                        * Decimal(str(component.weight_percentage))
                        / Decimal("100")
                        for component in components
                    ),
                    start=Decimal("0"),
                )
                final_score = round_final_score(weighted_score)
            rows.append(
                StudentGradeRow(
                    student_id=student.id,
                    student_code=student.student_code,
                    full_name=student.full_name,
                    email=student.user.email,
                    scores={
                        component_id: float(score) if score is not None else None
                        for component_id, score in decimal_scores.items()
                    },
                    final_score=float(final_score) if final_score is not None else None,
                )
            )
        return GradeBook(
            section_id=section.id,
            section_code=section.section_code,
            components=component_dtos,
            items=rows,
        )

    def save_grades(self, user: User, section_id: int, request: GradeUpdateRequest) -> GradeBook:
        self._section(user, section_id)
        registrations = self.records.list_roster(section_id)
        roster_ids = {registration.student.id for registration in registrations}
        components = self.records.list_components(section_id)
        component_by_id = {component.id: component for component in components}
        submitted_ids = [item.student_id for item in request.items]
        if len(set(submitted_ids)) != len(submitted_ids) or not set(submitted_ids) <= roster_ids:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                details=[field_error("items", "Danh sách sinh viên không thuộc lớp học phần")],
            )
        for item in request.items:
            if set(item.scores) != set(component_by_id):
                raise AppError(
                    ErrorCode.VALIDATION_ERROR,
                    details=[
                        field_error(
                            "scores",
                            "Mỗi sinh viên phải gửi điểm cho đúng các cột điểm đã cấu hình",
                        )
                    ],
                )
            for component_id, score in item.scores.items():
                component = component_by_id[component_id]
                if score is not None and (score < 0 or score > Decimal(str(component.max_score))):
                    raise AppError(
                        ErrorCode.VALIDATION_ERROR,
                        details=[
                            field_error(
                                "scores",
                                f"Điểm {component.name} phải nằm trong khoảng 0 đến {component.max_score}",
                            )
                        ],
                    )
                self.records.save_grade(
                    component_id=component_id,
                    student_id=item.student_id,
                    score=score,
                    updated_by_user_id=user.id,
                )
        self.db.commit()
        return self.gradebook(user, section_id)

    def export_attendance(self, user: User, section_id: int) -> BytesIO:
        section = self._section(user, section_id)
        registrations = self.records.list_roster(section_id)
        records = self.records.all_attendance(section_id)
        status_labels = {
            "PRESENT": "Có mặt",
            "ABSENT": "Vắng",
            "LATE": "Muộn",
            "EXCUSED": "Có phép",
        }
        attendance_map = {
            (record.student_id, record.class_date): status_labels[record.status.value]
            for record in records
        }
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Diem danh"
        class_dates = self._class_dates(section)
        headers = ["MSSV", "Họ và tên", *[class_date.isoformat() for class_date in class_dates]]
        sheet.append(headers)
        self._style_header(sheet)
        for registration in registrations:
            student = registration.student
            sheet.append(
                [
                    self._safe_excel_text(student.student_code),
                    self._safe_excel_text(student.full_name),
                    *[
                        attendance_map.get((student.id, class_date), "")
                        for class_date in class_dates
                    ],
                ]
            )
        sheet.freeze_panes = "C2"
        sheet.auto_filter.ref = sheet.dimensions
        sheet.column_dimensions["A"].width = 16
        sheet.column_dimensions["B"].width = 30
        for index in range(3, len(headers) + 1):
            sheet.column_dimensions[sheet.cell(1, index).column_letter].width = 14
        return self._workbook_bytes(workbook)

    def export_gradebook(self, user: User, section_id: int) -> BytesIO:
        gradebook = self.gradebook(user, section_id)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Bang diem"
        headers = [
            "MSSV",
            "Họ và tên",
            *[
                self._safe_excel_text(
                    f"{component.name} ({component.weight_percentage}%, tối đa {component.max_score})"
                )
                for component in gradebook.components
            ],
            "Điểm tổng kết",
        ]
        sheet.append(headers)
        self._style_header(sheet)
        for student in gradebook.items:
            sheet.append(
                [
                    self._safe_excel_text(student.student_code),
                    self._safe_excel_text(student.full_name),
                    *[
                        float(student.scores[component.id])
                        if student.scores[component.id] is not None
                        else None
                        for component in gradebook.components
                    ],
                    float(student.final_score) if student.final_score is not None else None,
                ]
            )
        sheet.freeze_panes = "C2"
        sheet.auto_filter.ref = sheet.dimensions
        sheet.column_dimensions["A"].width = 16
        sheet.column_dimensions["B"].width = 30
        for index in range(3, len(headers) + 1):
            sheet.column_dimensions[sheet.cell(1, index).column_letter].width = 24
        return self._workbook_bytes(workbook)

    @staticmethod
    def _class_dates(section: CourseSection) -> list[date]:
        first_date = section.semester.start_date + timedelta(days=section.day_of_week - 2)
        return [
            first_date + timedelta(weeks=week - 1)
            for week in range(section.start_week, section.end_week + 1)
        ]

    @staticmethod
    def _style_header(sheet) -> None:
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="A6192E")
        sheet.row_dimensions[1].height = 30

    @staticmethod
    def _safe_excel_text(value: str) -> str:
        if value.lstrip().startswith(("=", "+", "-", "@")):
            return f"'{value}"
        return value

    @staticmethod
    def _workbook_bytes(workbook: Workbook) -> BytesIO:
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return output
