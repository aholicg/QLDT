"""API regression coverage for the student registration portal (UC005/UC006).

The test exercises the portal-facing section projection and the complete
register -> list registrations -> cancel -> refresh lifecycle using the
in-memory SQLite fixtures. It does not require MySQL or a running gateway.
"""

from datetime import date

from sqlalchemy import select

from app.entity import CourseSection, Lecturer, Room, Semester, Subject
from tests.conftest import login


def _registration_portal_world(db_session):
    lecturer = db_session.scalars(select(Lecturer)).first()
    assert lecturer is not None

    semester = Semester(
        semester_code="2026.1",
        name="Học kỳ 1 năm học 2026-2027",
        start_date=date(2026, 9, 7),
        end_date=date(2027, 1, 18),
        num_weeks=20,
    )
    room = Room(room_code="REG-PORTAL-01", building="TEST", capacity=30)
    subject = Subject(
        subject_code="REGPORTAL",
        name="Kiểm thử cổng đăng ký",
        credits=3,
    )
    db_session.add_all([semester, room, subject])
    db_session.flush()

    section = CourseSection(
        section_code="REG-PORTAL-01",
        subject_id=subject.id,
        semester_id=semester.id,
        lecturer_id=lecturer.id,
        room_id=room.id,
        day_of_week=4,
        start_period=1,
        end_period=3,
        start_week=1,
        end_week=20,
        max_capacity=1,
        current_enrollment=0,
    )
    db_session.add(section)
    db_session.commit()
    return semester, section


def test_registration_portal_register_refresh_and_cancel_regression(client, db_session):
    """Catalog seat state, registration identity, duplicate guard and cancellation stay aligned."""
    student_headers = login(client, "sv1", "Sv@12345")
    semester, section = _registration_portal_world(db_session)
    params = {"semesterId": semester.id, "page": 1, "size": 50}

    # Before registration, the catalog advertises one free seat and no ownership.
    catalog_before = client.get("/api/sections", params=params, headers=student_headers)
    assert catalog_before.status_code == 200, catalog_before.text
    catalog_page = catalog_before.json()
    assert {"items", "page", "size", "totalItems", "totalPages"} <= set(catalog_page)
    before = next(item for item in catalog_page["items"] if item["id"] == section.id)
    assert before["currentEnrollment"] == 0
    assert before["remainingSeats"] == 1
    assert before["full"] is False
    assert before["registeredByMe"] is False

    # A successful write returns the canonical registration and nested section.
    created = client.post(
        "/api/registrations",
        json={"sectionId": section.id},
        headers=student_headers,
    )
    assert created.status_code == 201, created.text
    registration = created.json()
    registration_id = registration["id"]
    assert registration["section"]["id"] == section.id
    assert registration["section"]["registeredByMe"] is True

    # Duplicate registration is rejected without consuming another seat.
    duplicate = client.post(
        "/api/registrations",
        json={"sectionId": section.id},
        headers=student_headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"] == "ALREADY_REGISTERED"

    mine_after_register = client.get(
        "/api/registrations/me",
        params={"semesterId": semester.id},
        headers=student_headers,
    )
    assert mine_after_register.status_code == 200, mine_after_register.text
    registered_items = mine_after_register.json()["items"]
    assert [item["id"] for item in registered_items] == [registration_id]

    catalog_after_register = client.get(
        "/api/sections", params=params, headers=student_headers
    )
    assert catalog_after_register.status_code == 200, catalog_after_register.text
    after_register = next(
        item for item in catalog_after_register.json()["items"] if item["id"] == section.id
    )
    assert after_register["currentEnrollment"] == 1
    assert after_register["remainingSeats"] == 0
    assert after_register["full"] is True
    assert after_register["registeredByMe"] is True

    # Cancellation returns 204, removes the student's registration and restores the seat.
    cancelled = client.delete(
        f"/api/registrations/{registration_id}",
        headers=student_headers,
    )
    assert cancelled.status_code == 204, cancelled.text

    mine_after_cancel = client.get(
        "/api/registrations/me",
        params={"semesterId": semester.id},
        headers=student_headers,
    )
    assert mine_after_cancel.status_code == 200, mine_after_cancel.text
    assert mine_after_cancel.json()["items"] == []

    catalog_after_cancel = client.get(
        "/api/sections", params=params, headers=student_headers
    )
    assert catalog_after_cancel.status_code == 200, catalog_after_cancel.text
    after_cancel = next(
        item for item in catalog_after_cancel.json()["items"] if item["id"] == section.id
    )
    assert after_cancel["currentEnrollment"] == 0
    assert after_cancel["remainingSeats"] == 1
    assert after_cancel["full"] is False
    assert after_cancel["registeredByMe"] is False


def test_registration_portal_requires_student_authentication(client):
    """Registration reads and writes remain protected at the API boundary."""
    assert client.get("/api/registrations/me").status_code == 401
    assert client.post("/api/registrations", json={"sectionId": 1}).status_code == 401

    lecturer_headers = login(client, "gv1", "Gv@12345")
    assert client.get("/api/registrations/me", headers=lecturer_headers).status_code == 403
    assert (
        client.post(
            "/api/registrations",
            json={"sectionId": 1},
            headers=lecturer_headers,
        ).status_code
        == 403
    )
