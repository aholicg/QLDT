from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.core.config import Settings
from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.dto.registration.registration import RegisterRequest
from app.entity.auth.lecturer import Lecturer
from app.entity.auth.student import Student
from app.entity.auth.user import User
from app.entity.catalog.course_section import CourseSection
from app.entity.catalog.room import Room
from app.entity.catalog.semester import Semester
from app.entity.catalog.subject import Subject
from app.entity.registration.registration import Registration as RegistrationEntity
from app.service.registration.registration_service import RegistrationService


@pytest.fixture()
def registration_world(db_session):
    lecturer = db_session.scalars(select(Lecturer)).first()
    semester = Semester(
        semester_code="2026.1",
        name="Học kỳ 1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 1),
        num_weeks=15,
    )
    room = Room(room_code="D9-301", capacity=100)
    db_session.add_all([semester, room])
    db_session.flush()

    def add_section(
        section_code: str,
        subject_code: str,
        credits: int,
        *,
        day: int = 2,
        start_period: int = 1,
        max_capacity: int = 30,
    ) -> CourseSection:
        subject = Subject(
            subject_code=subject_code,
            name=subject_code,
            credits=credits,
        )
        db_session.add(subject)
        db_session.flush()
        section = CourseSection(
            section_code=section_code,
            subject_id=subject.id,
            semester_id=semester.id,
            lecturer_id=lecturer.id,
            room_id=room.id,
            day_of_week=day,
            start_period=start_period,
            end_period=start_period + 1,
            start_week=1,
            end_week=15,
            max_capacity=max_capacity,
            current_enrollment=0,
        )
        db_session.add(section)
        db_session.flush()
        return section

    db_session.commit()
    return {
        "semester": semester,
        "add_section": add_section,
        "student": db_session.scalars(select(User).where(User.username == "sv1")).first(),
    }


def _register(db_session, user, section):
    return RegistrationService(db_session).register(user, RegisterRequest(section_id=section.id))


def _add_existing_registration(db_session, student_id: int, section: CourseSection):
    section.current_enrollment += 1
    registration = RegistrationEntity(student_id=student_id, section_id=section.id)
    db_session.add(registration)
    db_session.commit()
    return registration


def test_register_success_increments_enrollment(db_session, registration_world):
    section = registration_world["add_section"]("SEC-1", "SUB-1", 6)

    registration = _register(db_session, registration_world["student"], section)

    db_session.refresh(section)
    assert registration.section.id == section.id
    assert registration.section.registered_by_me is True
    assert section.current_enrollment == 1


def test_register_missing_section_returns_not_found(db_session, registration_world):
    with pytest.raises(AppError) as error:
        _register(db_session, registration_world["student"], CourseSection(id=9999))

    assert error.value.code == ErrorCode.NOT_FOUND


def test_register_rejects_duplicate_section(db_session, registration_world):
    section = registration_world["add_section"]("SEC-1", "SUB-1", 6)
    _register(db_session, registration_world["student"], section)

    with pytest.raises(AppError) as error:
        _register(db_session, registration_world["student"], section)

    assert error.value.code == ErrorCode.ALREADY_REGISTERED


def test_register_rejects_same_subject_in_another_section(db_session, registration_world):
    first = registration_world["add_section"]("SEC-1", "SUB-1", 6)
    second = registration_world["add_section"]("SEC-2", "SUB-1-OTHER", 6, day=3, start_period=3)
    second.subject_id = first.subject_id
    db_session.commit()
    _register(db_session, registration_world["student"], first)

    with pytest.raises(AppError) as error:
        _register(db_session, registration_world["student"], second)

    assert error.value.code == ErrorCode.SAME_SUBJECT_REGISTERED


def test_register_rejects_schedule_conflict_with_section_code_details(
    db_session, registration_world
):
    first = registration_world["add_section"]("SEC-1", "SUB-1", 6)
    conflicting = registration_world["add_section"]("SEC-2", "SUB-2", 6)
    _register(db_session, registration_world["student"], first)

    with pytest.raises(AppError) as error:
        _register(db_session, registration_world["student"], conflicting)

    assert error.value.code == ErrorCode.STUDENT_SCHEDULE_CONFLICT
    assert error.value.details[0]["field"] == "sectionCode"
    assert "SEC-1" in error.value.details[0]["message"]


def test_register_rejects_full_section(db_session, registration_world):
    section = registration_world["add_section"]("SEC-1", "SUB-1", 6, max_capacity=1)
    another_user = db_session.scalars(select(User).where(User.username == "locked")).first()
    another_student = Student(user_id=another_user.id, student_code="20210002")
    db_session.add(another_student)
    db_session.flush()
    _add_existing_registration(db_session, another_student.id, section)

    with pytest.raises(AppError) as error:
        _register(db_session, registration_world["student"], section)

    db_session.refresh(section)
    assert error.value.code == ErrorCode.CLASS_FULL
    assert section.current_enrollment == 1


def test_register_over_credit_limit_does_not_increase_enrollment(db_session, registration_world):
    current = registration_world["add_section"]("SEC-1", "SUB-1", 20, day=2)
    attempted = registration_world["add_section"]("SEC-2", "SUB-2", 5, day=3)
    _register(db_session, registration_world["student"], current)

    with pytest.raises(AppError) as error:
        _register(db_session, registration_world["student"], attempted)

    db_session.refresh(attempted)
    assert error.value.code == ErrorCode.CREDIT_LIMIT_EXCEEDED
    assert {detail["field"] for detail in error.value.details} == {
        "currentCredits",
        "maxCredits",
    }
    assert attempted.current_enrollment == 0


def test_register_at_exact_credit_limit_is_allowed(db_session, registration_world):
    first = registration_world["add_section"]("SEC-1", "SUB-1", 12, day=2)
    second = registration_world["add_section"]("SEC-2", "SUB-2", 12, day=3)
    _register(db_session, registration_world["student"], first)

    _register(db_session, registration_world["student"], second)

    db_session.refresh(second)
    assert second.current_enrollment == 1


def test_cancel_below_minimum_is_allowed(db_session, registration_world):
    section = registration_world["add_section"]("SEC-1", "SUB-1", 12)
    registration = _register(db_session, registration_world["student"], section)

    RegistrationService(db_session).cancel(registration_world["student"], registration.id)

    db_session.refresh(section)
    assert section.current_enrollment == 0
    assert db_session.get(RegistrationEntity, registration.id) is None


def test_cancel_before_student_reaches_minimum_is_allowed(db_session, registration_world):
    section = registration_world["add_section"]("SEC-1", "SUB-1", 8)
    registration = _register(db_session, registration_world["student"], section)

    RegistrationService(db_session).cancel(registration_world["student"], registration.id)

    db_session.refresh(section)
    assert section.current_enrollment == 0
    assert db_session.get(RegistrationEntity, registration.id) is None


def test_cancel_rejects_registration_owned_by_another_student(db_session, registration_world):
    section = registration_world["add_section"]("SEC-1", "SUB-1", 6)
    another_user = db_session.scalars(select(User).where(User.username == "locked")).first()
    another_student = Student(user_id=another_user.id, student_code="20210002")
    db_session.add(another_student)
    db_session.flush()
    registration = _add_existing_registration(db_session, another_student.id, section)

    with pytest.raises(AppError) as error:
        RegistrationService(db_session).cancel(registration_world["student"], registration.id)

    assert error.value.code == ErrorCode.FORBIDDEN


def test_cancel_missing_registration_returns_not_found(db_session, registration_world):
    with pytest.raises(AppError) as error:
        RegistrationService(db_session).cancel(registration_world["student"], 9999)

    assert error.value.code == ErrorCode.NOT_FOUND


def test_list_mine_filters_to_semester_and_returns_sections(db_session, registration_world):
    section = registration_world["add_section"]("SEC-1", "SUB-1", 6)
    _register(db_session, registration_world["student"], section)

    result = RegistrationService(db_session).list_mine(
        registration_world["student"], registration_world["semester"].id
    )

    assert len(result.items) == 1
    assert result.items[0].section.id == section.id
    assert result.items[0].section.registered_by_me is True


def test_settings_credit_limit_defaults():
    config = Settings(
        _env_file=None,
        mysql_password="local-only",
        jwt_secret="a" * 32,
        database_url="sqlite://",
    )

    assert config.min_credits_per_semester == 12
    assert config.max_credits_per_semester == 24


def test_settings_reject_maximum_below_minimum():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            mysql_password="local-only",
            jwt_secret="a" * 32,
            database_url="sqlite://",
            min_credits_per_semester=13,
            max_credits_per_semester=12,
        )


def test_settings_reject_maximum_below_one():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            mysql_password="local-only",
            jwt_secret="a" * 32,
            database_url="sqlite://",
            min_credits_per_semester=0,
            max_credits_per_semester=0,
        )


def test_settings_credit_limits_are_read_from_environment(monkeypatch):
    monkeypatch.setenv("MYSQL_PASSWORD", "local-only")
    monkeypatch.setenv("JWT_SECRET", "a" * 32)
    monkeypatch.setenv("MIN_CREDITS_PER_SEMESTER", "9")
    monkeypatch.setenv("MAX_CREDITS_PER_SEMESTER", "21")

    config = Settings(_env_file=None, database_url="sqlite://")

    assert config.min_credits_per_semester == 9
    assert config.max_credits_per_semester == 21
