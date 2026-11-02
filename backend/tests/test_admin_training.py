"""Kiểm thử chức năng quản trị đào tạo (Feature 10): UC002, UC003.

Bộ test chạy với SQLite trong bộ nhớ qua fixture `client`/`db_session`.
Bộ dữ liệu thử nghiệm cho FE-BE-DB thật nằm ở `backend/scripts/seed_test_data.py`
và được kiểm thử tích hợp trong `backend/tests/integration/`.

Ghi chú nghiệp vụ: hệ thống không còn ràng buộc môn tiên quyết/song hành; các
test dưới đây cũng kiểm tra hợp đồng API và schema CSDL không chứa hai khái niệm này.
"""

import json
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select

from app.entity import CourseSection, Lecturer, Role, Room, Semester, Student, Subject, User
from app.security.password import hash_password
from tests.conftest import login


@pytest.fixture()
def training_world(db_session):
    """Dữ liệu nền cho các test quản trị: 2 học kỳ, 2 phòng, 2 môn, 2 giảng viên, 2 sinh viên."""
    semester = Semester(
        semester_code="2026.1",
        name="Học kỳ 1 2026-2027",
        start_date=date(2026, 9, 7),
        end_date=date(2027, 1, 18),
        num_weeks=20,
    )
    old_semester = Semester(
        semester_code="2025.2",
        name="Học kỳ 2 2025-2026",
        start_date=date(2025, 9, 8),
        end_date=date(2026, 1, 18),
        num_weeks=18,
    )
    room_a = Room(room_code="TST-101", building="TST", capacity=60)
    room_b = Room(room_code="TST-102", building="TST", capacity=30)
    subject_a = Subject(subject_code="TST101", name="Kiểm thử phần mềm", credits=3)
    subject_b = Subject(subject_code="TST102", name="Quản trị cơ sở dữ liệu", credits=4)
    db_session.add_all([semester, old_semester, room_a, room_b, subject_a, subject_b])
    db_session.flush()

    gv1 = db_session.scalars(select(Lecturer).where(Lecturer.lecturer_code == "GV001")).one()
    gv2_user = User(
        username="gv2",
        password_hash=hash_password("Gv2@12345"),
        full_name="Giảng viên Kiểm thử",
        email="gv2@sis.edu.vn",
        role=Role.LECTURER,
    )
    sv2_user = User(
        username="sv2",
        password_hash=hash_password("Sv2@12345"),
        full_name="Sinh viên Kiểm thử",
        email="sv2@sis.edu.vn",
        role=Role.STUDENT,
    )
    db_session.add_all([gv2_user, sv2_user])
    db_session.flush()
    gv2 = Lecturer(user_id=gv2_user.id, lecturer_code="GV002")
    sv2 = Student(user_id=sv2_user.id, student_code="20210002", cohort="K66", major="CNTT")
    db_session.add_all([gv2, sv2])
    db_session.commit()

    return {
        "semester": semester,
        "old_semester": old_semester,
        "room_a": room_a,
        "room_b": room_b,
        "subject_a": subject_a,
        "subject_b": subject_b,
        "gv1": gv1,
        "gv2": gv2,
        "sv2": sv2,
    }


def _admin(client):
    return login(client, "admin", "Admin@123")


def _student(client):
    return login(client, "sv1", "Sv@12345")


def _student2(client):
    return login(client, "sv2", "Sv2@12345")


def _lecturer(client):
    return login(client, "gv1", "Gv@12345")


def _lecturer2(client):
    return login(client, "gv2", "Gv2@12345")


def _section_payload(world, section_code, **overrides):
    payload = {
        "sectionCode": section_code,
        "subjectId": world["subject_a"].id,
        "semesterId": world["semester"].id,
        "lecturerId": world["gv1"].id,
        "roomId": world["room_a"].id,
        "dayOfWeek": 2,
        "startPeriod": 1,
        "endPeriod": 3,
        "startWeek": 1,
        "endWeek": 15,
        "maxCapacity": 40,
    }
    payload.update(overrides)
    return payload


def _update_payload(world, section_code, **overrides):
    payload = _section_payload(world, section_code, **overrides)
    payload.pop("sectionCode")
    return payload


def _create_section(client, headers, world, section_code, **overrides):
    res = client.post(
        "/api/sections", json=_section_payload(world, section_code, **overrides), headers=headers
    )
    assert res.status_code == 201, res.text
    return res.json()


def _register(client, headers, section_id):
    res = client.post("/api/registrations", json={"sectionId": section_id}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def test_admin_reads_training_lookups_and_semesters(client, training_world):
    admin = _admin(client)

    semesters = client.get("/api/semesters", headers=admin)
    assert semesters.status_code == 200
    codes = {item["semesterCode"] for item in semesters.json()["items"]}
    assert {"2026.1", "2025.2"} <= codes

    current = client.get("/api/semesters/current", headers=admin)
    assert current.status_code == 200
    assert current.json()["semesterCode"] == "2026.1"
    assert "currentWeek" in current.json()

    lookups = client.get("/api/sections/lookups", headers=admin)
    assert lookups.status_code == 200
    body = lookups.json()
    assert any(item["subjectCode"] == "TST101" for item in body["subjects"])
    assert any(item["lecturerCode"] == "GV001" for item in body["lecturers"])
    assert any(item["roomCode"] == "TST-101" for item in body["rooms"])
    assert any(item["semesterCode"] == "2026.1" for item in body["semesters"])

    subjects = client.get("/api/subjects", headers=admin)
    assert subjects.status_code == 200
    page = subjects.json()
    assert {"items", "page", "size", "totalItems", "totalPages"} <= set(page)


def test_non_admin_cannot_manage_subjects_or_sections(client, training_world):
    for headers in (_student(client), _lecturer(client)):
        create_subject = client.post(
            "/api/subjects",
            json={"subjectCode": "TST900", "name": "Không được phép", "credits": 3},
            headers=headers,
        )
        assert create_subject.status_code == 403

        create_section = client.post(
            "/api/sections", json=_section_payload(training_world, "TST-S900"), headers=headers
        )
        assert create_section.status_code == 403

        assert client.get("/api/sections/lookups", headers=headers).status_code == 403
        assert (
            client.put(
                f"/api/subjects/{training_world['subject_a'].id}",
                json={"name": "Không được phép", "credits": 3},
                headers=headers,
            ).status_code
            == 403
        )
        assert (
            client.delete(
                f"/api/sections/{training_world['subject_a'].id}", headers=headers
            ).status_code
            == 403
        )

    assert client.get("/api/sections", headers=_student(client)).status_code == 200
    assert client.get("/api/sections", headers=_lecturer(client)).status_code == 403


def test_subject_crud_and_delete_guard(client, training_world):
    admin = _admin(client)

    created = client.post(
        "/api/subjects",
        json={
            "subjectCode": "TST200",
            "name": "Môn học quản trị thử nghiệm",
            "credits": 3,
            "description": "Tạo bởi test quản trị",
        },
        headers=admin,
    )
    assert created.status_code == 201, created.text
    subject = created.json()
    assert subject["subjectCode"] == "TST200"
    assert subject["sectionCount"] == 0

    duplicate = client.post(
        "/api/subjects",
        json={"subjectCode": "TST200", "name": "Môn trùng mã", "credits": 3},
        headers=admin,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"] == "DUPLICATE_CODE"
    assert duplicate.json()["details"][0]["field"] == "subjectCode"

    listed = client.get(
        "/api/subjects",
        params={"keyword": "TST200", "page": 1, "size": 10},
        headers=admin,
    )
    assert listed.status_code == 200
    assert listed.json()["totalItems"] == 1
    assert listed.json()["items"][0]["id"] == subject["id"]

    detail = client.get(f"/api/subjects/{subject['id']}", headers=admin)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Môn học quản trị thử nghiệm"

    updated = client.put(
        f"/api/subjects/{subject['id']}",
        json={"name": "Môn học đã cập nhật", "credits": 4, "description": "Đã sửa"},
        headers=admin,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Môn học đã cập nhật"
    assert updated.json()["credits"] == 4

    section = _create_section(
        client, admin, training_world, "TST-S200", subjectId=subject["id"], dayOfWeek=6
    )
    blocked = client.delete(f"/api/subjects/{subject['id']}", headers=admin)
    assert blocked.status_code == 409
    assert blocked.json()["error"] == "SUBJECT_HAS_SECTIONS"

    assert client.delete(f"/api/sections/{section['id']}", headers=admin).status_code == 204
    assert client.delete(f"/api/subjects/{subject['id']}", headers=admin).status_code == 204
    assert client.get(f"/api/subjects/{subject['id']}", headers=admin).status_code == 404


def test_subject_validation_reports_camel_case_fields(client):
    res = client.post(
        "/api/subjects",
        json={"subjectCode": "", "name": "", "credits": 0},
        headers=_admin(client),
    )
    assert res.status_code == 400
    assert res.json()["error"] == "VALIDATION_ERROR"
    fields = {detail["field"] for detail in res.json()["details"]}
    assert {"subjectCode", "name", "credits"} <= fields


def test_section_crud_and_response_fields(client, training_world):
    admin = _admin(client)

    created = _create_section(client, admin, training_world, "TST-S201")
    assert created["sectionCode"] == "TST-S201"
    assert created["subject"]["id"] == training_world["subject_a"].id
    assert created["semester"]["id"] == training_world["semester"].id
    assert created["lecturer"]["lecturerCode"] == "GV001"
    assert created["room"]["roomCode"] == "TST-101"
    assert created["currentEnrollment"] == 0
    assert created["remainingSeats"] == 40
    assert created["full"] is False
    assert created["registeredByMe"] is None

    detail = client.get(f"/api/sections/{created['id']}", headers=admin)
    assert detail.status_code == 200
    assert detail.json()["sectionCode"] == "TST-S201"

    listed = client.get(
        "/api/sections",
        params={
            "semesterId": training_world["semester"].id,
            "keyword": "TST-S201",
            "page": 1,
            "size": 10,
        },
        headers=admin,
    )
    assert listed.status_code == 200
    assert listed.json()["totalItems"] == 1
    assert listed.json()["items"][0]["id"] == created["id"]

    updated = client.put(
        f"/api/sections/{created['id']}",
        json=_update_payload(
            training_world,
            "TST-S201",
            dayOfWeek=3,
            startPeriod=4,
            endPeriod=6,
            maxCapacity=50,
        ),
        headers=admin,
    )
    assert updated.status_code == 200
    assert updated.json()["dayOfWeek"] == 3
    assert updated.json()["startPeriod"] == 4
    assert updated.json()["maxCapacity"] == 50
    assert updated.json()["remainingSeats"] == 50

    assert client.delete(f"/api/sections/{created['id']}", headers=admin).status_code == 204
    assert client.get(f"/api/sections/{created['id']}", headers=admin).status_code == 404


@pytest.mark.parametrize("field", ["subjectId", "semesterId", "lecturerId", "roomId"])
def test_section_rejects_missing_references(client, training_world, field):
    payload = _section_payload(training_world, f"TST-S{field}")
    payload[field] = 999999
    res = client.post("/api/sections", json=payload, headers=_admin(client))
    assert res.status_code == 404
    assert res.json()["error"] == "NOT_FOUND"
    assert res.json()["details"][0]["field"] == field


def test_section_rejects_duplicate_code_and_invalid_values(client, training_world):
    admin = _admin(client)
    _create_section(client, admin, training_world, "TST-S202", dayOfWeek=7)

    duplicate = client.post(
        "/api/sections",
        json=_section_payload(training_world, "TST-S202", dayOfWeek=7),
        headers=admin,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"] == "DUPLICATE_CODE"
    assert duplicate.json()["details"][0]["field"] == "sectionCode"

    bad_period = client.post(
        "/api/sections",
        json=_section_payload(training_world, "TST-S203", startPeriod=5, endPeriod=3, dayOfWeek=7),
        headers=admin,
    )
    assert bad_period.status_code == 400
    assert "endPeriod" in {detail["field"] for detail in bad_period.json()["details"]}

    bad_week = client.post(
        "/api/sections",
        json=_section_payload(training_world, "TST-S204", endWeek=30, dayOfWeek=7),
        headers=admin,
    )
    assert bad_week.status_code == 400
    assert "endWeek" in {detail["field"] for detail in bad_week.json()["details"]}

    over_capacity = client.post(
        "/api/sections",
        json=_section_payload(
            training_world,
            "TST-S205",
            maxCapacity=training_world["room_a"].capacity + 1,
            dayOfWeek=7,
        ),
        headers=admin,
    )
    assert over_capacity.status_code == 400
    assert "maxCapacity" in {detail["field"] for detail in over_capacity.json()["details"]}

    bad_day = client.post(
        "/api/sections",
        json=_section_payload(training_world, "TST-S206", dayOfWeek=1),
        headers=admin,
    )
    assert bad_day.status_code == 400
    assert "dayOfWeek" in {detail["field"] for detail in bad_day.json()["details"]}


def test_section_detects_room_and_lecturer_conflicts(client, training_world):
    admin = _admin(client)
    _create_section(
        client,
        admin,
        training_world,
        "TST-C01",
        roomId=training_world["room_a"].id,
        lecturerId=training_world["gv1"].id,
        dayOfWeek=2,
        startPeriod=1,
        endPeriod=3,
    )

    room_conflict = client.post(
        "/api/sections",
        json=_section_payload(
            training_world,
            "TST-C02",
            roomId=training_world["room_a"].id,
            lecturerId=training_world["gv2"].id,
            dayOfWeek=2,
            startPeriod=2,
            endPeriod=4,
        ),
        headers=admin,
    )
    assert room_conflict.status_code == 409
    assert room_conflict.json()["error"] == "SCHEDULE_CONFLICT"
    assert {detail["field"] for detail in room_conflict.json()["details"]} == {"roomId"}

    lecturer_conflict = client.post(
        "/api/sections",
        json=_section_payload(
            training_world,
            "TST-C03",
            roomId=training_world["room_b"].id,
            lecturerId=training_world["gv1"].id,
            dayOfWeek=2,
            startPeriod=3,
            endPeriod=5,
            maxCapacity=30,
        ),
        headers=admin,
    )
    assert lecturer_conflict.status_code == 409
    assert lecturer_conflict.json()["error"] == "SCHEDULE_CONFLICT"
    assert {detail["field"] for detail in lecturer_conflict.json()["details"]} == {"lecturerId"}

    _create_section(
        client,
        admin,
        training_world,
        "TST-C04",
        roomId=training_world["room_a"].id,
        lecturerId=training_world["gv2"].id,
        dayOfWeek=3,
        startPeriod=1,
        endPeriod=3,
    )
    _create_section(
        client,
        admin,
        training_world,
        "TST-C05",
        roomId=training_world["room_b"].id,
        lecturerId=training_world["gv1"].id,
        dayOfWeek=2,
        startPeriod=4,
        endPeriod=6,
        maxCapacity=30,
    )


def test_admin_schedule_update_reports_student_conflict_structure(client, training_world):
    admin = _admin(client)
    student = _student(client)
    first = _create_section(
        client,
        admin,
        training_world,
        "SEC-STUDENT-1",
        dayOfWeek=2,
        startPeriod=1,
        endPeriod=3,
    )
    second = _create_section(
        client,
        admin,
        training_world,
        "SEC-STUDENT-2",
        subjectId=training_world["subject_b"].id,
        lecturerId=training_world["gv2"].id,
        roomId=training_world["room_b"].id,
        dayOfWeek=3,
        startPeriod=5,
        endPeriod=6,
        maxCapacity=30,
    )
    _register(client, student, first["id"])
    _register(client, student, second["id"])

    update = client.put(
        f"/api/sections/{second['id']}",
        headers=admin,
        json=_update_payload(
            training_world,
            "SEC-STUDENT-2",
            subjectId=training_world["subject_b"].id,
            lecturerId=training_world["gv2"].id,
            roomId=training_world["room_b"].id,
            dayOfWeek=2,
            startPeriod=2,
            endPeriod=4,
            maxCapacity=30,
        ),
    )
    assert update.status_code == 409, update.text
    assert update.json()["error"] == "SCHEDULE_CONFLICT"
    detail = update.json()["details"][0]
    assert detail["type"] == "STUDENT"
    assert detail["sectionA"] == "SEC-STUDENT-2"
    assert detail["sectionB"] == "SEC-STUDENT-1"
    assert detail["studentCode"] == "20210001"
    assert detail["dayOfWeek"] == 2
    assert detail["periods"] == {"start": 2, "end": 3}
    assert detail["weeks"] == {"start": 1, "end": 15}


def test_section_update_guards_capacity_and_enrolled_identity(client, training_world, db_session):
    admin = _admin(client)
    student1 = _student(client)
    student2 = _student2(client)
    section = _create_section(client, admin, training_world, "TST-S207", maxCapacity=5)
    _register(client, student1, section["id"])
    _register(client, student2, section["id"])

    below_enrollment = client.put(
        f"/api/sections/{section['id']}",
        json=_update_payload(training_world, "TST-S207", maxCapacity=1),
        headers=admin,
    )
    assert below_enrollment.status_code == 409
    assert below_enrollment.json()["error"] == "CAPACITY_BELOW_ENROLLMENT"
    assert below_enrollment.json()["details"][0]["field"] == "maxCapacity"

    change_subject = client.put(
        f"/api/sections/{section['id']}",
        json=_update_payload(
            training_world,
            "TST-S207",
            subjectId=training_world["subject_b"].id,
            maxCapacity=5,
        ),
        headers=admin,
    )
    assert change_subject.status_code == 409
    assert change_subject.json()["error"] == "SECTION_HAS_REGISTRATIONS"

    change_semester = client.put(
        f"/api/sections/{section['id']}",
        json=_update_payload(
            training_world,
            "TST-S207",
            semesterId=training_world["old_semester"].id,
            maxCapacity=5,
        ),
        headers=admin,
    )
    assert change_semester.status_code == 409
    assert change_semester.json()["error"] == "SECTION_HAS_REGISTRATIONS"

    allowed = client.put(
        f"/api/sections/{section['id']}",
        json=_update_payload(
            training_world,
            "TST-S207",
            roomId=training_world["room_b"].id,
            dayOfWeek=4,
            startPeriod=7,
            endPeriod=9,
            startWeek=2,
            endWeek=16,
            maxCapacity=5,
        ),
        headers=admin,
    )
    assert allowed.status_code == 200, allowed.text
    detail = client.get(f"/api/sections/{section['id']}", headers=admin)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["room"]["roomCode"] == "TST-102"
    assert body["currentEnrollment"] == 2
    assert body["remainingSeats"] == 3

    entity = db_session.get(CourseSection, section["id"])
    assert entity is not None
    assert entity.current_enrollment == 2


def test_section_delete_guard_and_registration_cancel(client, training_world):
    admin = _admin(client)
    student = _student(client)
    section = _create_section(client, admin, training_world, "TST-S208", maxCapacity=10)
    registration = _register(client, student, section["id"])

    blocked = client.delete(f"/api/sections/{section['id']}", headers=admin)
    assert blocked.status_code == 409
    assert blocked.json()["error"] == "SECTION_HAS_REGISTRATIONS"

    assert (
        client.delete(f"/api/registrations/{registration['id']}", headers=student).status_code
        == 204
    )
    assert client.delete(f"/api/sections/{section['id']}", headers=admin).status_code == 204


def test_admin_roster_access_and_payload(client, training_world):
    admin = _admin(client)
    section = _create_section(client, admin, training_world, "TST-S209", maxCapacity=10)
    _register(client, _student(client), section["id"])
    _register(client, _student2(client), section["id"])

    roster = client.get(f"/api/sections/{section['id']}/students", headers=admin)
    assert roster.status_code == 200
    body = roster.json()
    assert body["sectionId"] == section["id"]
    assert body["sectionCode"] == "TST-S209"
    assert body["currentEnrollment"] == 2
    assert body["maxCapacity"] == 10
    assert {item["studentCode"] for item in body["items"]} == {"20210001", "20210002"}
    assert {"id", "studentCode", "fullName", "email", "cohort", "major", "registeredAt"} <= set(
        body["items"][0]
    )
    assert body["items"][0]["registeredAt"].endswith("+07:00")

    owner = client.get(f"/api/sections/{section['id']}/students", headers=_lecturer(client))
    assert owner.status_code == 200

    other_lecturer = client.get(
        f"/api/sections/{section['id']}/students", headers=_lecturer2(client)
    )
    assert other_lecturer.status_code == 403

    student = client.get(f"/api/sections/{section['id']}/students", headers=_student(client))
    assert student.status_code == 403

    assert client.get("/api/sections/999999/students", headers=admin).status_code == 404


def test_registration_does_not_require_prerequisite_or_corequisite(client, training_world):
    admin = _admin(client)
    student = _student(client)
    first = _create_section(
        client, admin, training_world, "TST-S210", dayOfWeek=5, startPeriod=1, endPeriod=3
    )
    second = _create_section(
        client,
        admin,
        training_world,
        "TST-S211",
        subjectId=training_world["subject_b"].id,
        dayOfWeek=5,
        startPeriod=4,
        endPeriod=6,
    )

    _register(client, student, first["id"])
    _register(client, student, second["id"])

    mine = client.get(
        "/api/registrations/me",
        params={"semesterId": training_world["semester"].id},
        headers=student,
    )
    assert mine.status_code == 200
    assert {item["section"]["sectionCode"] for item in mine.json()["items"]} == {
        "TST-S210",
        "TST-S211",
    }


def test_contract_and_database_schema_have_no_prerequisite_or_corequisite(client, training_world):
    openapi = client.get("/api/openapi.json")
    assert openapi.status_code == 200
    payload = json.dumps(openapi.json()).lower()
    for term in ("prerequisite", "corequisite", "prerequisite_subject", "corequisite_subject"):
        assert term not in payload

    schemas = openapi.json()["components"]["schemas"]
    section_create = schemas["SectionCreateRequest"]
    assert {
        "sectionCode",
        "subjectId",
        "semesterId",
        "lecturerId",
        "roomId",
        "dayOfWeek",
        "startPeriod",
        "endPeriod",
        "startWeek",
        "endWeek",
        "maxCapacity",
    } <= set(section_create["properties"])
    assert "subjectCode" not in section_create["properties"]

    subject_properties = schemas["Subject"]["properties"]
    assert {
        "id",
        "subjectCode",
        "name",
        "credits",
        "description",
        "sectionCount",
    } <= set(subject_properties)

    register_properties = schemas["RegisterRequest"]["properties"]
    assert "sectionId" in register_properties

    schema_sql = (
        (Path(__file__).resolve().parents[2] / "db" / "schema.sql")
        .read_text(encoding="utf-8")
        .lower()
    )
    assert "prerequisite" not in schema_sql
    assert "corequisite" not in schema_sql
