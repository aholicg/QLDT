from sqlalchemy import func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import joinedload

from app.entity.auth.lecturer import Lecturer
from app.entity.catalog.course_section import CourseSection
from app.entity.catalog.subject import Subject
from app.entity.registration.registration import Registration
from app.repository.base import BaseRepository


class SectionRepository(BaseRepository):
    def get_by_id(self, section_id: int) -> CourseSection | None:
        stmt = (
            select(CourseSection)
            .options(
                joinedload(CourseSection.subject),
                joinedload(CourseSection.semester),
                joinedload(CourseSection.lecturer).joinedload(Lecturer.user),
                joinedload(CourseSection.room),
            )
            .where(CourseSection.id == section_id)
        )
        return self.db.scalars(stmt).first()

    def search(
        self,
        semester_id: int,
        subject_id: int | None,
        keyword: str | None,
        unit_keyword: str | None,
        offset: int,
        limit: int,
        sort: str | None,
    ) -> tuple[list[CourseSection], int]:
        """Trả (danh sách CourseSection, tổng số). dùng joinedload để tránh N+1."""
        stmt = (
            select(CourseSection)
            .join(CourseSection.subject)
            .options(
                joinedload(CourseSection.subject),
                joinedload(CourseSection.semester),
                joinedload(CourseSection.lecturer).joinedload(Lecturer.user),
                joinedload(CourseSection.room),
            )
            .where(CourseSection.semester_id == semester_id)
        )
        count_stmt = (
            select(func.count(CourseSection.id))
            .join(CourseSection.subject)
            .where(CourseSection.semester_id == semester_id)
        )

        if subject_id is not None:
            stmt = stmt.where(CourseSection.subject_id == subject_id)
            count_stmt = count_stmt.where(CourseSection.subject_id == subject_id)

        if keyword:
            kw = f"%{keyword.strip()}%"
            condition = or_(
                CourseSection.section_code.ilike(kw),
                Subject.subject_code.ilike(kw),
                Subject.name.ilike(kw),
            )
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        if unit_keyword:
            unit_kw = f"%{unit_keyword.strip()}%"
            unit_condition = Subject.description.ilike(unit_kw)
            stmt = stmt.where(unit_condition)
            count_stmt = count_stmt.where(unit_condition)

        total = self.db.scalar(count_stmt) or 0
        stmt = (
            stmt.order_by(CourseSection.day_of_week.asc(), CourseSection.start_period.asc())
            .offset(offset)
            .limit(limit)
        )
        items = list(self.db.scalars(stmt).all())
        return items, total

    def list_by_lecturer(self, lecturer_id: int, semester_id: int) -> list[CourseSection]:
        stmt = (
            select(CourseSection)
            .options(
                joinedload(CourseSection.subject),
                joinedload(CourseSection.semester),
                joinedload(CourseSection.lecturer).joinedload(Lecturer.user),
                joinedload(CourseSection.room),
            )
            .where(
                CourseSection.lecturer_id == lecturer_id,
                CourseSection.semester_id == semester_id,
            )
            .order_by(CourseSection.day_of_week.asc(), CourseSection.start_period.asc())
        )
        return list(self.db.scalars(stmt).all())

    def exists_by_code(self, section_code: str) -> bool:
        stmt = select(CourseSection.id).where(CourseSection.section_code == section_code)
        return self.db.scalars(stmt).first() is not None

    def count_registrations(self, section_id: int) -> int:
        stmt = select(func.count(Registration.id)).where(Registration.section_id == section_id)
        return self.db.scalar(stmt) or 0

    def add(self, section: CourseSection) -> CourseSection:
        self.db.add(section)
        self.db.flush()
        return section

    def delete(self, section: CourseSection) -> None:
        self.db.delete(section)
        self.db.flush()

    def find_room_or_lecturer_conflicts(
        self,
        *,
        semester_id: int,
        room_id: int,
        lecturer_id: int,
        day_of_week: int,
        start_period: int,
        end_period: int,
        start_week: int,
        end_week: int,
        target_section_code: str = "__TARGET__",
        exclude_section_id: int | None = None,
    ) -> list[CourseSection]:
        """Tìm lớp giao thời gian trong cùng học kỳ, trùng phòng hoặc giảng viên."""
        return [
            section
            for section, _ in self.find_room_or_lecturer_conflict_details(
                semester_id=semester_id,
                room_id=room_id,
                lecturer_id=lecturer_id,
                day_of_week=day_of_week,
                start_period=start_period,
                end_period=end_period,
                start_week=start_week,
                end_week=end_week,
                target_section_code=target_section_code,
                exclude_section_id=exclude_section_id,
            )
        ]

    def find_room_or_lecturer_conflict_details(
        self,
        *,
        semester_id: int,
        room_id: int,
        lecturer_id: int,
        day_of_week: int,
        start_period: int,
        end_period: int,
        start_week: int,
        end_week: int,
        target_section_code: str = "__TARGET__",
        exclude_section_id: int | None = None,
    ) -> list[tuple[CourseSection, dict]]:
        stmt = (
            select(CourseSection)
            .options(joinedload(CourseSection.subject))
            .where(
                CourseSection.semester_id == semester_id,
                CourseSection.day_of_week == day_of_week,
                or_(CourseSection.room_id == room_id, CourseSection.lecturer_id == lecturer_id),
            )
        )
        if exclude_section_id is not None:
            stmt = stmt.where(CourseSection.id != exclude_section_id)
        candidates = list(self.db.scalars(stmt).all())
        if not candidates:
            return []

        from app.service.timetable.conflict_engine import find_conflicts

        target = {
            "sectionCode": target_section_code,
            "dayOfWeek": day_of_week,
            "startPeriod": start_period,
            "endPeriod": end_period,
            "startWeek": start_week,
            "endWeek": end_week,
            "roomId": room_id,
            "lecturerId": lecturer_id,
        }
        conflicts = find_conflicts([target, *candidates])
        if not conflicts:
            return []

        by_code = {section.section_code: section for section in candidates}
        return [
            (
                by_code[conflict["sectionB"]],
                {
                    **conflict,
                    "sectionA": conflict["sectionA"],
                    "sectionB": (
                        by_code[conflict["sectionB"]].section_code
                        if conflict["sectionB"] != target_section_code
                        else None
                    ),
                },
            )
            for conflict in conflicts
            if conflict["sectionA"] == target_section_code and conflict["sectionB"] in by_code
        ]

    def increment_enrollment_if_available(self, section_id: int) -> bool:
        """UPDATE ... SET current_enrollment = current_enrollment + 1
        WHERE section_id = :id AND current_enrollment < max_capacity.
        True nếu tăng được; False (0 dòng bị ảnh hưởng) nghĩa là lớp đã đầy -> CLASS_FULL."""
        result: CursorResult = self.db.execute(  # type: ignore[assignment]
            update(CourseSection)
            .where(
                CourseSection.id == section_id,
                CourseSection.current_enrollment < CourseSection.max_capacity,
            )
            .values(current_enrollment=CourseSection.current_enrollment + 1)
        )
        return result.rowcount == 1

    def decrement_enrollment(self, section_id: int) -> None:
        self.db.execute(
            update(CourseSection)
            .where(CourseSection.id == section_id, CourseSection.current_enrollment > 0)
            .values(current_enrollment=CourseSection.current_enrollment - 1)
        )
