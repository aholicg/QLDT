from datetime import date

from app.entity import Role, Room, Semester, Student, Subject, User
from app.security.password import hash_password
from tests.conftest import login


def _seed_basic_catalog(db_session):
    semester = Semester(
        semester_code="2026.1",
        name="Học kỳ 1 2026-2027",
        start_date=date(2026, 9, 7),
        end_date=date(2026, 12, 20),
        num_weeks=15,
    )
    room = Room(room_code="D9-301", building="D9", capacity=60)
    subject = Subject(subject_code="IT3180", name="Công nghệ phần mềm", credits=3)
    db_session.add_all([semester, room, subject])
    db_session.commit()
    return semester, room, subject


def test_uc006_atomic_change_section_success_and_failures(client, db_session):
    """UC006: Đổi lớp học phần nguyên tử (Atomic Change Section).
    - Đổi thành công sang lớp khác cùng môn: sĩ số lớp cũ giảm 1, sĩ số lớp mới tăng 1.
    - Đổi sang lớp khác môn -> 400 VALIDATION_ERROR.
    - Đổi sang lớp đã đầy -> 409 CLASS_FULL (vẫn giữ nguyên lớp cũ, không bị mất chỗ).
    """
    student_headers = login(client, "sv1", "Sv@12345")
    admin_headers = login(client, "admin", "Admin@123")
    semester, room, subject = _seed_basic_catalog(db_session)

    # Môn thứ 2 để test chặn đổi khác môn
    sub2 = Subject(subject_code="IT3090", name="Cơ sở dữ liệu", credits=3)
    db_session.add(sub2)
    db_session.commit()

    # Tạo 2 lớp của cùng môn IT3180
    sec1 = client.post(
        "/api/sections",
        json={
            "sectionCode": "CHG-101",
            "subjectId": subject.id,
            "semesterId": semester.id,
            "lecturerId": 1,
            "roomId": room.id,
            "dayOfWeek": 2,
            "startPeriod": 1,
            "endPeriod": 3,
            "startWeek": 1,
            "endWeek": 15,
            "maxCapacity": 30,
        },
        headers=admin_headers,
    ).json()

    sec2 = client.post(
        "/api/sections",
        json={
            "sectionCode": "CHG-102",
            "subjectId": subject.id,
            "semesterId": semester.id,
            "lecturerId": 1,
            "roomId": room.id,
            "dayOfWeek": 3,
            "startPeriod": 1,
            "endPeriod": 3,
            "startWeek": 1,
            "endWeek": 15,
            "maxCapacity": 1,  # chỉ chứa 1 chỗ
        },
        headers=admin_headers,
    ).json()

    # Tạo lớp của môn IT3090
    sec_diff_sub = client.post(
        "/api/sections",
        json={
            "sectionCode": "CHG-201",
            "subjectId": sub2.id,
            "semesterId": semester.id,
            "lecturerId": 1,
            "roomId": room.id,
            "dayOfWeek": 4,
            "startPeriod": 1,
            "endPeriod": 3,
            "startWeek": 1,
            "endWeek": 15,
            "maxCapacity": 30,
        },
        headers=admin_headers,
    ).json()

    # Sinh viên 1 đăng ký lớp 101
    reg_res = client.post(
        "/api/registrations", json={"sectionId": sec1["id"]}, headers=student_headers
    )
    assert reg_res.status_code == 201
    reg_id = reg_res.json()["id"]

    # 1. Thử đổi sang lớp khác môn -> 400
    res_diff = client.put(
        f"/api/registrations/{reg_id}/change",
        json={"newSectionId": sec_diff_sub["id"]},
        headers=student_headers,
    )
    assert res_diff.status_code == 400
    assert res_diff.json()["error"] == "VALIDATION_ERROR"

    # 2. Đổi thành công sang lớp CHG-102 (cùng môn IT3180)
    res_chg = client.put(
        f"/api/registrations/{reg_id}/change",
        json={"newSectionId": sec2["id"]},
        headers=student_headers,
    )
    assert res_chg.status_code == 200
    assert res_chg.json()["section"]["id"] == sec2["id"]
    assert res_chg.json()["section"]["sectionCode"] == "CHG-102"

    # Kiểm tra sĩ số: lớp 101 giảm về 0, lớp 102 tăng lên 1 (đầy 1/1)
    chk1 = client.get(f"/api/sections/{sec1['id']}", headers=admin_headers).json()
    chk2 = client.get(f"/api/sections/{sec2['id']}", headers=admin_headers).json()
    assert chk1["currentEnrollment"] == 0
    assert chk2["currentEnrollment"] == 1
    assert chk2["full"] is True

    # 3. Tạo sinh viên thứ 2, đăng ký vào lớp 101, rồi thử đổi sang 102 (đã đầy) -> bị 409 CLASS_FULL
    user_sv2 = User(
        username="sv2_chg",
        password_hash=hash_password("Sv@12345"),
        full_name="Sinh viên 2",
        role=Role.STUDENT,
    )
    db_session.add(user_sv2)
    db_session.flush()
    student_sv2 = Student(user_id=user_sv2.id, student_code="20268888")
    db_session.add(student_sv2)
    db_session.commit()

    sv2_headers = login(client, "sv2_chg", "Sv@12345")
    reg2_res = client.post(
        "/api/registrations", json={"sectionId": sec1["id"]}, headers=sv2_headers
    )
    assert reg2_res.status_code == 201
    reg2_id = reg2_res.json()["id"]

    # Thử đổi sang lớp 102 đang đầy -> 409 CLASS_FULL
    res_full = client.put(
        f"/api/registrations/{reg2_id}/change",
        json={"newSectionId": sec2["id"]},
        headers=sv2_headers,
    )
    assert res_full.status_code == 409
    assert res_full.json()["error"] == "CLASS_FULL"

    # Đảm bảo sinh viên 2 vẫn được giữ nguyên vị trí ở lớp 101, không bị mất chỗ!
    chk1_after = client.get(f"/api/sections/{sec1['id']}", headers=admin_headers).json()
    assert chk1_after["currentEnrollment"] == 1
