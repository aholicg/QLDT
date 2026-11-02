"""Kiểm thử tích hợp FE-BE-DB cho chức năng quản trị đào tạo (Feature 10).

Yêu cầu: MySQL, backend, gateway và (tùy chọn) frontend đang chạy; bộ dữ liệu
chuẩn đã được nạp. Các test tự bỏ qua khi thiếu thành phần, nên `pytest` mặc
định vẫn chạy được chỉ với SQLite.

Chạy riêng:
    pytest -m integration
"""

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.entity import (
    CourseSection,
    Lecturer,
    Registration,
    Role,
    Room,
    Semester,
    Student,
    Subject,
    User,
)
from app.security.password import hash_password

pytestmark = pytest.mark.integration

STUDENT_PASSWORD = "Test@12345"


def _unique(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:8].upper()}"


def _section_payload(env: dict, subject_id: int, section_code: str, **overrides) -> dict:
    payload = {
        "sectionCode": section_code,
        "subjectId": subject_id,
        "semesterId": env["semester_id"],
        "lecturerId": env["lecturer_id"],
        "roomId": env["room_id"],
        "dayOfWeek": 2,
        "startPeriod": 1,
        "endPeriod": 3,
        "startWeek": 1,
        "endWeek": 15,
        "maxCapacity": 50,
    }
    payload.update(overrides)
    return payload


def _create_subject(api, headers, code: str) -> dict:
    response = api.post(
        "/subjects",
        json={
            "subjectCode": code,
            "name": f"Môn tích hợp {code}",
            "credits": 3,
            "description": "Dữ liệu do kiểm thử tích hợp tạo",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def training_env(db_engine) -> Iterator[dict]:
    """Tạo giảng viên, phòng và hai sinh viên riêng cho test, dọn sạch sau khi chạy."""
    suffix = uuid.uuid4().hex[:8].upper()
    with Session(db_engine) as db:
        semester_id = db.scalar(select(Semester.id).where(Semester.semester_code == "2026.1"))
        if semester_id is None:
            pytest.skip("Chưa có học kỳ 2026.1; hãy chạy seed chuẩn trước")

        lecturer_user = User(
            username=f"tstlect{suffix.lower()}",
            password_hash=hash_password(STUDENT_PASSWORD),
            full_name="Giảng viên tích hợp",
            email=f"tstlect{suffix.lower()}@qldt.test",
            role=Role.LECTURER,
        )
        db.add(lecturer_user)
        db.flush()
        lecturer = Lecturer(
            user_id=lecturer_user.id,
            lecturer_code=f"TL{suffix}",
            department="Bộ môn Kiểm thử tích hợp",
        )
        room = Room(room_code=f"TR-{suffix}", building="TST", capacity=80)
        db.add_all([lecturer, room])
        db.flush()

        student_users: list[User] = []
        students: list[Student] = []
        for index in (1, 2):
            user = User(
                username=f"tstsv{suffix.lower()}{index}",
                password_hash=hash_password(STUDENT_PASSWORD),
                full_name=f"Sinh viên tích hợp {index}",
                email=f"tstsv{suffix.lower()}{index}@qldt.test",
                role=Role.STUDENT,
            )
            db.add(user)
            db.flush()
            student = Student(
                user_id=user.id,
                student_code=f"TS{suffix}{index}",
                cohort="K2026",
                major="Kiểm thử tích hợp",
            )
            db.add(student)
            db.flush()
            student_users.append(user)
            students.append(student)

        context = {
            "semester_id": semester_id,
            "lecturer_id": lecturer.id,
            "room_id": room.id,
            "student_ids": [student.id for student in students],
            "student_codes": [student.student_code for student in students],
            "student_usernames": [user.username for user in student_users],
            "user_ids": [lecturer_user.id, *(user.id for user in student_users)],
            "subject_ids": [],
            "section_ids": [],
        }
        db.commit()

    yield context

    with Session(db_engine) as db:
        section_ids = list(context["section_ids"])
        section_ids.extend(
            db.scalars(
                select(CourseSection.id).where(CourseSection.lecturer_id == context["lecturer_id"])
            )
        )
        section_ids = sorted(set(section_ids))
        if section_ids:
            db.execute(delete(Registration).where(Registration.section_id.in_(section_ids)))
        if context["student_ids"]:
            db.execute(
                delete(Registration).where(Registration.student_id.in_(context["student_ids"]))
            )
        if section_ids:
            db.execute(delete(CourseSection).where(CourseSection.id.in_(section_ids)))
        if context["subject_ids"]:
            db.execute(delete(Subject).where(Subject.id.in_(context["subject_ids"])))
        if context["student_ids"]:
            db.execute(delete(Student).where(Student.id.in_(context["student_ids"])))
        db.execute(delete(Lecturer).where(Lecturer.id == context["lecturer_id"]))
        if context["user_ids"]:
            db.execute(delete(User).where(User.id.in_(context["user_ids"])))
        db.execute(delete(Room).where(Room.id == context["room_id"]))
        db.commit()


def test_gateway_and_backend_health(gateway_client):
    health = gateway_client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert "X-Request-Id" in health.headers

    backend = gateway_client.get("/health/backend")
    assert backend.status_code == 200
    assert backend.json()["status"] == "ok"


def test_admin_lookups_match_mysql(api, admin_headers, db_engine):
    me = api.get("/auth/me", headers=admin_headers)
    assert me.status_code == 200
    assert me.json()["user"]["role"] == "ADMIN"

    lookups = api.get("/sections/lookups", headers=admin_headers)
    assert lookups.status_code == 200
    body = lookups.json()

    with db_engine.connect() as connection:
        counts = {
            table: connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            for table in ("SUBJECTS", "LECTURERS", "ROOMS", "SEMESTERS")
        }

    assert len(body["subjects"]) == counts["SUBJECTS"]
    assert len(body["lecturers"]) == counts["LECTURERS"]
    assert len(body["rooms"]) == counts["ROOMS"]
    assert len(body["semesters"]) == counts["SEMESTERS"]


def test_admin_subject_crud_persists_to_mysql(api, admin_headers, db_engine, training_env):
    code = _unique("TSTI")
    created = _create_subject(api, admin_headers, code)
    training_env["subject_ids"].append(created["id"])

    with db_engine.connect() as connection:
        row = (
            connection.execute(
                text("SELECT name, credits FROM SUBJECTS WHERE subject_code = :code"),
                {"code": code},
            )
            .mappings()
            .one()
        )
    assert row["name"] == f"Môn tích hợp {code}"
    assert row["credits"] == 3

    updated = api.put(
        f"/subjects/{created['id']}",
        json={"name": f"Đã sửa {code}", "credits": 4, "description": "Cập nhật từ test"},
        headers=admin_headers,
    )
    assert updated.status_code == 200, updated.text

    with db_engine.connect() as connection:
        row = (
            connection.execute(
                text("SELECT name, credits FROM SUBJECTS WHERE subject_code = :code"),
                {"code": code},
            )
            .mappings()
            .one()
        )
    assert row["name"] == f"Đã sửa {code}"
    assert row["credits"] == 4

    assert api.delete(f"/subjects/{created['id']}", headers=admin_headers).status_code == 204
    with db_engine.connect() as connection:
        row = connection.execute(
            text("SELECT subject_id FROM SUBJECTS WHERE subject_code = :code"),
            {"code": code},
        ).first()
    assert row is None
    training_env["subject_ids"].remove(created["id"])


def test_admin_section_crud_and_conflict_persist_to_mysql(
    api, admin_headers, db_engine, training_env
):
    subject = _create_subject(api, admin_headers, _unique("TSTI"))
    training_env["subject_ids"].append(subject["id"])
    code = _unique("TSTS")
    payload = _section_payload(training_env, subject["id"], code)

    created = api.post("/sections", json=payload, headers=admin_headers)
    assert created.status_code == 201, created.text
    section = created.json()
    training_env["section_ids"].append(section["id"])

    with db_engine.connect() as connection:
        row = (
            connection.execute(
                text(
                    "SELECT section_code, day_of_week, max_capacity "
                    "FROM COURSE_SECTIONS WHERE section_id = :section_id"
                ),
                {"section_id": section["id"]},
            )
            .mappings()
            .one()
        )
    assert row["section_code"] == code
    assert row["day_of_week"] == 2
    assert row["max_capacity"] == 50

    conflict = api.post(
        "/sections",
        json={**payload, "sectionCode": f"{code}C", "startPeriod": 2, "endPeriod": 4},
        headers=admin_headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"] == "SCHEDULE_CONFLICT"

    update_payload = {key: value for key, value in payload.items() if key != "sectionCode"}
    update_payload.update({"dayOfWeek": 3, "startPeriod": 4, "endPeriod": 6})
    updated = api.put(f"/sections/{section['id']}", json=update_payload, headers=admin_headers)
    assert updated.status_code == 200, updated.text

    with db_engine.connect() as connection:
        row = (
            connection.execute(
                text("SELECT day_of_week FROM COURSE_SECTIONS WHERE section_id = :section_id"),
                {"section_id": section["id"]},
            )
            .mappings()
            .one()
        )
    assert row["day_of_week"] == 3

    assert api.delete(f"/sections/{section['id']}", headers=admin_headers).status_code == 204
    training_env["section_ids"].remove(section["id"])


def test_admin_roster_matches_mysql_registrations(api, admin_headers, db_engine, training_env):
    subject = _create_subject(api, admin_headers, _unique("TSTI"))
    training_env["subject_ids"].append(subject["id"])
    code = _unique("TSTR")
    section = api.post(
        "/sections",
        json=_section_payload(
            training_env, subject["id"], code, dayOfWeek=5, startPeriod=1, endPeriod=3
        ),
        headers=admin_headers,
    )
    assert section.status_code == 201, section.text
    section_body = section.json()
    training_env["section_ids"].append(section_body["id"])

    for username in training_env["student_usernames"]:
        login = api.post("/auth/login", json={"username": username, "password": STUDENT_PASSWORD})
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['accessToken']}"}
        registration = api.post(
            "/registrations", json={"sectionId": section_body["id"]}, headers=headers
        )
        assert registration.status_code == 201, registration.text

    roster = api.get(f"/sections/{section_body['id']}/students", headers=admin_headers)
    assert roster.status_code == 200, roster.text
    body = roster.json()
    assert body["currentEnrollment"] == 2
    assert {item["studentCode"] for item in body["items"]} == set(training_env["student_codes"])

    with db_engine.connect() as connection:
        registration_count = connection.execute(
            text("SELECT COUNT(*) FROM REGISTRATIONS WHERE section_id = :section_id"),
            {"section_id": section_body["id"]},
        ).scalar_one()
        enrollment = connection.execute(
            text("SELECT current_enrollment FROM COURSE_SECTIONS WHERE section_id = :section_id"),
            {"section_id": section_body["id"]},
        ).scalar_one()
    assert registration_count == 2
    assert enrollment == 2


def test_frontend_proxy_reaches_backend_and_database(api, frontend_client):
    page = frontend_client.get("/")
    assert page.status_code == 200
    assert "text/html" in page.headers.get("content-type", "")

    proxied = frontend_client.get("/api/subjects", params={"page": 1, "size": 1})
    assert proxied.status_code == 200, proxied.text
    direct = api.get("/subjects", params={"page": 1, "size": 1})
    assert direct.status_code == 200
    assert proxied.json()["totalItems"] == direct.json()["totalItems"]


def test_feature10_dataset_is_visible_through_api(api, admin_headers):
    subjects = api.get(
        "/subjects",
        params={"keyword": "TST101", "page": 1, "size": 10},
        headers=admin_headers,
    )
    assert subjects.status_code == 200
    if subjects.json()["totalItems"] == 0:
        pytest.skip("Chưa nạp bộ dữ liệu Feature 10; chạy python -m scripts.seed_test_data")

    semesters = api.get("/semesters", headers=admin_headers)
    assert semesters.status_code == 200
    semester_id = next(
        item["id"] for item in semesters.json()["items"] if item["semesterCode"] == "2026.1"
    )
    sections = api.get(
        "/sections",
        params={"semesterId": semester_id, "keyword": "TST-S03", "page": 1, "size": 10},
        headers=admin_headers,
    )
    assert sections.status_code == 200
    assert sections.json()["totalItems"] == 1
    section = sections.json()["items"][0]
    assert section["sectionCode"] == "TST-S03"
    assert section["maxCapacity"] == 1
    assert section["currentEnrollment"] >= 1
