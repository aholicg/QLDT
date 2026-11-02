from datetime import date
from decimal import Decimal
from io import BytesIO

from openpyxl import load_workbook
from sqlalchemy import select

from app.dto.registration.academic_records import round_final_score
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
from app.service.registration.academic_records_service import AcademicRecordsService
from tests.conftest import login


def _admin(client):
    return login(client, "admin", "Admin@123")


def _lecturer(client):
    return login(client, "gv1", "Gv@12345")


def _student(client):
    return login(client, "sv1", "Sv@12345")


def _unassigned_lecturer(client, db_session):
    user = User(
        username="gv2",
        password_hash=hash_password("Gv2@12345"),
        full_name="Giảng viên không phụ trách",
        email="gv2@sis.edu.vn",
        role=Role.LECTURER,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(Lecturer(user_id=user.id, lecturer_code="GV002"))
    db_session.commit()
    return login(client, "gv2", "Gv2@12345")


def _configure_grade_components(client, section_id):
    response = client.put(
        f"/api/sections/{section_id}/grade-components",
        headers=_admin(client),
        json={
            "items": [
                {"name": "Giữa kỳ", "weightPercentage": 50, "maxScore": 10},
                {"name": "Cuối kỳ", "weightPercentage": 50, "maxScore": 10},
            ]
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["items"]


def test_final_score_rounds_to_nearest_half_point():
    assert round_final_score(Decimal("8.3")) == Decimal("8.5")
    assert round_final_score(Decimal("8.2")) == Decimal("8.0")


def test_excel_text_escapes_formula_prefixes():
    assert AcademicRecordsService._safe_excel_text('=HYPERLINK("https://example.com")') == (
        '\'=HYPERLINK("https://example.com")'
    )


def _academic_world(db_session):
    lecturer = db_session.scalars(select(Lecturer)).first()
    student = db_session.scalars(select(Student)).first()
    semester = Semester(
        semester_code="2026.1",
        name="Học kỳ 1",
        start_date=date(2026, 9, 7),
        end_date=date(2026, 12, 31),
        num_weeks=15,
    )
    room = Room(room_code="D9-301", capacity=60)
    subject = Subject(subject_code="IT101", name="Kiểm thử phần mềm", credits=3)
    db_session.add_all([semester, room, subject])
    db_session.flush()
    section = CourseSection(
        section_code="IT101-01",
        subject_id=subject.id,
        semester_id=semester.id,
        lecturer_id=lecturer.id,
        room_id=room.id,
        day_of_week=2,
        start_period=1,
        end_period=3,
        start_week=1,
        end_week=15,
        max_capacity=60,
        current_enrollment=1,
    )
    db_session.add(section)
    db_session.flush()
    db_session.add(Registration(student_id=student.id, section_id=section.id))
    db_session.commit()
    return {"section": section, "student": student}


def test_attendance_is_saved_for_scheduled_day_and_exported(client, db_session):
    world = _academic_world(db_session)
    section_id = world["section"].id
    headers = _lecturer(client)
    class_date = "2026-09-07"

    response = client.get(
        f"/api/sections/{section_id}/attendance",
        params={"classDate": class_date},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["status"] is None
    assert class_date in response.json()["scheduledDates"]

    save_response = client.put(
        f"/api/sections/{section_id}/attendance",
        headers=headers,
        json={
            "classDate": class_date,
            "items": [{"studentId": world["student"].id, "status": "LATE"}],
        },
    )
    assert save_response.status_code == 200
    assert save_response.json()["items"][0]["status"] == "LATE"

    invalid_date = client.get(
        f"/api/sections/{section_id}/attendance",
        params={"classDate": "2026-09-08"},
        headers=headers,
    )
    assert invalid_date.status_code == 400
    assert invalid_date.json()["details"][0]["field"] == "classDate"

    export_response = client.get(
        f"/api/sections/{section_id}/exports/attendance",
        headers=headers,
    )
    assert export_response.status_code == 200
    assert (
        export_response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert (
        f"filename*=UTF-8''diem-danh-lop-{section_id}.xlsx"
        in export_response.headers["content-disposition"]
    )
    workbook = load_workbook(BytesIO(export_response.content), read_only=True)
    sheet = workbook["Diem danh"]
    assert list(sheet.iter_rows(min_row=1, max_row=1, values_only=True))[0][:3] == (
        "MSSV",
        "Họ và tên",
        class_date,
    )
    assert sheet["A2"].value == "20210001"
    assert sheet["B2"].value == "Trần Thị B"
    assert sheet["C2"].value == "Muộn"
    assert sheet["D2"].value is None
    assert "diem-danh-lop" in export_response.headers["content-disposition"]
    workbook.close()


def test_gradebook_uses_weighted_scores_and_half_point_rounding(client, db_session):
    world = _academic_world(db_session)
    section_id = world["section"].id
    configure_response = client.put(
        f"/api/sections/{section_id}/grade-components",
        headers=_admin(client),
        json={
            "items": [
                {"name": "Giữa kỳ", "weightPercentage": 50, "maxScore": 10},
                {"name": "Cuối kỳ", "weightPercentage": 50, "maxScore": 10},
            ]
        },
    )
    assert configure_response.status_code == 200
    components = configure_response.json()["items"]

    save_response = client.put(
        f"/api/sections/{section_id}/grades",
        headers=_lecturer(client),
        json={
            "items": [
                {
                    "studentId": world["student"].id,
                    "scores": {
                        str(components[0]["id"]): 8.3,
                        str(components[1]["id"]): 8.2,
                    },
                }
            ]
        },
    )
    assert save_response.status_code == 200
    assert save_response.json()["items"][0]["finalScore"] == 8.5

    locked_response = client.put(
        f"/api/sections/{section_id}/grade-components",
        headers=_admin(client),
        json={
            "items": [
                {"name": "Tổng kết", "weightPercentage": 100, "maxScore": 10},
            ]
        },
    )
    assert locked_response.status_code == 409
    assert locked_response.json()["error"] == "GRADE_COMPONENTS_LOCKED"

    export_response = client.get(
        f"/api/sections/{section_id}/exports/grades",
        headers=_lecturer(client),
    )
    assert export_response.status_code == 200
    assert (
        export_response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert (
        f"filename*=UTF-8''bang-diem-lop-{section_id}.xlsx"
        in export_response.headers["content-disposition"]
    )
    workbook = load_workbook(BytesIO(export_response.content), read_only=True)
    sheet = workbook["Bang diem"]
    assert sheet.max_row == 2
    headers = list(sheet.iter_rows(min_row=1, max_row=1, values_only=True))[0]
    assert headers[:2] == ("MSSV", "Họ và tên")
    assert "Giữa kỳ" in headers[2]
    assert "Cuối kỳ" in headers[3]
    assert headers[4] == "Điểm tổng kết"
    assert sheet["A2"].value == "20210001"
    assert sheet["B2"].value == "Trần Thị B"
    assert sheet["C2"].value == 8.3
    assert sheet["D2"].value == 8.2
    assert sheet["E2"].value == 8.5
    workbook.close()


def test_exports_preserve_empty_attendance_and_unentered_grades(client, db_session):
    world = _academic_world(db_session)
    section_id = world["section"].id
    headers = _lecturer(client)
    components = _configure_grade_components(client, section_id)

    attendance_response = client.get(
        f"/api/sections/{section_id}/attendance",
        params={"classDate": "2026-09-07"},
        headers=headers,
    )
    assert attendance_response.status_code == 200
    assert attendance_response.json()["items"][0]["status"] is None

    gradebook_response = client.get(f"/api/sections/{section_id}/grades", headers=headers)
    assert gradebook_response.status_code == 200
    grade_row = gradebook_response.json()["items"][0]
    assert grade_row["scores"] == {
        str(components[0]["id"]): None,
        str(components[1]["id"]): None,
    }
    assert grade_row["finalScore"] is None

    attendance_export = client.get(
        f"/api/sections/{section_id}/exports/attendance", headers=headers
    )
    attendance_sheet = load_workbook(BytesIO(attendance_export.content), read_only=True)[
        "Diem danh"
    ]
    assert attendance_sheet["A2"].value == "20210001"
    assert attendance_sheet["C2"].value is None
    attendance_sheet.parent.close()

    grade_export = client.get(f"/api/sections/{section_id}/exports/grades", headers=headers)
    grade_sheet = load_workbook(BytesIO(grade_export.content), read_only=True)["Bang diem"]
    assert grade_sheet["A2"].value == "20210001"
    assert grade_sheet["C2"].value is None
    assert grade_sheet["D2"].value is None
    assert grade_sheet["E2"].value is None
    grade_sheet.parent.close()


def test_only_assigned_lecturer_can_access_academic_records(client, db_session):
    world = _academic_world(db_session)
    student_headers = _student(client)
    section_id = world["section"].id

    components = _configure_grade_components(client, section_id)
    assigned_lecturer = _lecturer(client)
    class_date = "2026-09-07"
    saved_attendance = client.put(
        f"/api/sections/{section_id}/attendance",
        headers=assigned_lecturer,
        json={
            "classDate": class_date,
            "items": [{"studentId": world["student"].id, "status": "PRESENT"}],
        },
    )
    assert saved_attendance.status_code == 200
    saved_grade = client.put(
        f"/api/sections/{section_id}/grades",
        headers=assigned_lecturer,
        json={
            "items": [
                {
                    "studentId": world["student"].id,
                    "scores": {
                        str(components[0]["id"]): 7,
                        str(components[1]["id"]): 8,
                    },
                }
            ]
        },
    )
    assert saved_grade.status_code == 200

    response = client.get(
        f"/api/sections/{section_id}/attendance",
        params={"classDate": class_date},
        headers=student_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"] == "FORBIDDEN"

    student_requests = [
        client.put(
            f"/api/sections/{section_id}/attendance",
            headers=student_headers,
            json={
                "classDate": class_date,
                "items": [{"studentId": world["student"].id, "status": "ABSENT"}],
            },
        ),
        client.get(f"/api/sections/{section_id}/grades", headers=student_headers),
        client.put(
            f"/api/sections/{section_id}/grades",
            headers=student_headers,
            json={
                "items": [
                    {
                        "studentId": world["student"].id,
                        "scores": {
                            str(components[0]["id"]): 1,
                            str(components[1]["id"]): 1,
                        },
                    }
                ]
            },
        ),
        client.get(f"/api/sections/{section_id}/exports/attendance", headers=student_headers),
        client.get(f"/api/sections/{section_id}/exports/grades", headers=student_headers),
    ]
    for denied_response in student_requests:
        assert denied_response.status_code == 403
        assert denied_response.json()["error"] == "FORBIDDEN"

    outsider_headers = _unassigned_lecturer(client, db_session)
    lecturer_requests = [
        client.get(
            f"/api/sections/{section_id}/attendance",
            params={"classDate": class_date},
            headers=outsider_headers,
        ),
        client.put(
            f"/api/sections/{section_id}/attendance",
            headers=outsider_headers,
            json={
                "classDate": class_date,
                "items": [{"studentId": world["student"].id, "status": "ABSENT"}],
            },
        ),
        client.get(f"/api/sections/{section_id}/grades", headers=outsider_headers),
        client.put(
            f"/api/sections/{section_id}/grades",
            headers=outsider_headers,
            json={
                "items": [
                    {
                        "studentId": world["student"].id,
                        "scores": {
                            str(components[0]["id"]): 1,
                            str(components[1]["id"]): 1,
                        },
                    }
                ]
            },
        ),
        client.get(f"/api/sections/{section_id}/exports/attendance", headers=outsider_headers),
        client.get(f"/api/sections/{section_id}/exports/grades", headers=outsider_headers),
    ]
    for denied_response in lecturer_requests:
        assert denied_response.status_code == 403
        assert denied_response.json()["error"] == "FORBIDDEN"

    confirmed_attendance = client.get(
        f"/api/sections/{section_id}/attendance",
        params={"classDate": class_date},
        headers=assigned_lecturer,
    )
    confirmed_gradebook = client.get(
        f"/api/sections/{section_id}/grades", headers=assigned_lecturer
    )
    assert confirmed_attendance.json()["items"][0]["status"] == "PRESENT"
    assert confirmed_gradebook.json()["items"][0]["scores"] == {
        str(components[0]["id"]): 7.0,
        str(components[1]["id"]): 8.0,
    }


def test_academic_records_endpoints_require_authentication(client, db_session):
    section_id = _academic_world(db_session)["section"].id
    endpoints = [
        ("GET", f"/api/sections/{section_id}/attendance"),
        ("PUT", f"/api/sections/{section_id}/attendance"),
        ("GET", f"/api/sections/{section_id}/grades"),
        ("PUT", f"/api/sections/{section_id}/grades"),
        ("GET", f"/api/sections/{section_id}/grade-components"),
        ("PUT", f"/api/sections/{section_id}/grade-components"),
        ("GET", f"/api/sections/{section_id}/exports/attendance"),
        ("GET", f"/api/sections/{section_id}/exports/grades"),
    ]
    bodies = {
        "PUT:/api/sections/{section_id}/attendance": {
            "classDate": "2026-09-07",
            "items": [{"studentId": 1, "status": "PRESENT"}],
        },
        "PUT:/api/sections/{section_id}/grades": {"items": []},
        "PUT:/api/sections/{section_id}/grade-components": {
            "items": [{"name": "Tổng kết", "weightPercentage": 100, "maxScore": 10}]
        },
    }

    for method, url in endpoints:
        body_key = f"{method}:/api/sections/{{section_id}}/{url.rsplit('/', 1)[-1]}"
        body = bodies.get(body_key)
        response = (
            client.request(method, url, json=body)
            if body is not None
            else client.request(method, url)
        )
        assert response.status_code == 401, f"{method} {url}: {response.text}"
        assert response.json()["error"] == "UNAUTHORIZED"
