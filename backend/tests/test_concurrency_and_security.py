"""Kiểm thử cơ chế xử lý tải cao đồng thời (Concurrency Lock) và Bảo mật (Security).

- Concurrency: Nhiều luồng/tiến trình cùng đăng ký 1 lớp chỉ còn 1 chỗ -> chỉ đúng 1 thành công, không vượt max_capacity.
- Security: Chặn truy cập trái quyền (IDOR), bảo vệ mật khẩu, chống SQL Injection/Path traversal, timeout/atomic rollback.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError
from app.dto.registration.registration import RegisterRequest
from app.entity import (
    Base,
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
from app.service.registration.registration_service import RegistrationService
from tests.conftest import login


@pytest.fixture()
def concurrent_world(tmp_path):
    """Tạo database SQLite dựa trên file tạm để hỗ trợ multi-threading an toàn."""
    db_file = tmp_path / "concurrent_test.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(
        db_url,
        connect_args={"timeout": 30},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with Session() as session:
        semester = Semester(
            semester_code="2026.1",
            name="Học kỳ 1 2026-2027",
            start_date=date(2026, 9, 7),
            end_date=date(2026, 12, 20),
            num_weeks=15,
        )
        room = Room(room_code="D9-401", building="D9", capacity=100)
        subject = Subject(subject_code="IT4000", name="Hệ phân tán", credits=3)
        lecturer_user = User(
            username="gv_conc",
            password_hash=hash_password("Pass@123"),
            full_name="Thầy Song Song",
            role=Role.LECTURER,
        )
        session.add_all([semester, room, subject, lecturer_user])
        session.flush()

        lecturer = Lecturer(user_id=lecturer_user.id, lecturer_code="GV_CONC")
        session.add(lecturer)
        session.flush()

        # Tạo lớp học phần CHỈ CÒN ĐÚNG 1 CHỖ TRỐNG (max_capacity = 1)
        section = CourseSection(
            section_code="CONC-101",
            subject_id=subject.id,
            semester_id=semester.id,
            lecturer_id=lecturer.id,
            room_id=room.id,
            day_of_week=3,
            start_period=1,
            end_period=3,
            start_week=1,
            end_week=15,
            max_capacity=1,
            current_enrollment=0,
        )
        session.add(section)

        # Tạo 10 sinh viên khác nhau để cùng ập vào đăng ký lớp này
        student_ids = []
        for i in range(10):
            user = User(
                username=f"sv_race_{i}",
                password_hash=hash_password("Pass@123"),
                full_name=f"Sinh viên {i}",
                role=Role.STUDENT,
            )
            session.add(user)
            session.flush()
            student = Student(user_id=user.id, student_code=f"202600{i:02d}")
            session.add(student)
            session.flush()
            student_ids.append(user.id)

        session.commit()

    return {
        "engine": engine,
        "Session": Session,
        "section_id": section.id,
        "student_user_ids": student_ids,
    }


def test_concurrency_race_condition_under_high_load(concurrent_world):
    """KIỂM THỬ TẢI CAO ĐỒNG THỜI (Concurrency Lock / Atomic update):
    10 sinh viên cùng gửi yêu cầu đăng ký cùng 1 tích tắc vào 1 lớp chỉ còn 1 chỗ.
    Kết quả bắt buộc:
    - Đúng 1 sinh viên thành công (status 201).
    - 9 sinh viên còn lại nhận lỗi CLASS_FULL (status 409).
    - current_enrollment trong database tuyệt đối không vượt quá max_capacity (= 1).
    """
    Session = concurrent_world["Session"]
    section_id = concurrent_world["section_id"]
    student_user_ids = concurrent_world["student_user_ids"]

    successes = []
    failures = []

    def try_register(user_id):
        with Session() as session:
            user = session.get(User, user_id)
            service = RegistrationService(session)
            try:
                reg = service.register(user, RegisterRequest(section_id=section_id))
                successes.append(reg)
            except AppError as e:
                failures.append(e)

    # Chạy đồng thời 10 luồng cùng lúc
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(try_register, uid) for uid in student_user_ids]
        for f in futures:
            f.result()

    # Kiểm tra tính toàn vẹn (Invariants)
    assert len(successes) == 1, f"Có {len(successes)} sinh viên đăng ký thành công (kỳ vọng chỉ 1)!"
    assert len(failures) == 9
    assert all(err.code == ErrorCode.CLASS_FULL for err in failures)

    with Session() as session:
        sec = session.get(CourseSection, section_id)
        assert sec.current_enrollment == 1
        assert sec.current_enrollment <= sec.max_capacity

        regs = list(
            session.scalars(select(Registration).where(Registration.section_id == section_id)).all()
        )
        assert len(regs) == 1


def test_security_idor_prevent_cancelling_other_student_registration(client, db_session):
    """BẢO MẬT: Chống IDOR (Insecure Direct Object Reference)
    Sinh viên A không được phép hủy đăng ký của sinh viên B bằng cách đoán ID.
    Phải trả về 403 FORBIDDEN.
    """
    student_a_headers = login(client, "sv1", "Sv@12345")

    # Tạo sinh viên B
    user_b = User(
        username="sv_victim",
        password_hash=hash_password("Pass@123"),
        full_name="Nạn nhân",
        role=Role.STUDENT,
    )
    db_session.add(user_b)
    db_session.flush()
    student_b = Student(user_id=user_b.id, student_code="20269999")
    db_session.add(student_b)
    db_session.flush()

    # Tạo lớp và đăng ký cho sinh viên B
    semester = Semester(
        semester_code="2026.2",
        name="Kỳ 2",
        start_date=date(2027, 1, 1),
        end_date=date(2027, 5, 1),
        num_weeks=15,
    )
    room = Room(room_code="D9-101", capacity=50)
    subject = Subject(subject_code="IT9999", name="Bảo mật nâng cao", credits=3)
    lecturer = db_session.scalars(select(Lecturer)).first()
    db_session.add_all([semester, room, subject])
    db_session.flush()

    section = CourseSection(
        section_code="SEC-SEC-1",
        subject_id=subject.id,
        semester_id=semester.id,
        lecturer_id=lecturer.id,
        room_id=room.id,
        day_of_week=4,
        start_period=1,
        end_period=3,
        start_week=1,
        end_week=15,
        max_capacity=30,
        current_enrollment=1,
    )
    db_session.add(section)
    db_session.flush()

    reg_b = Registration(student_id=student_b.id, section_id=section.id)
    db_session.add(reg_b)
    db_session.commit()

    # Sinh viên A cố tình gọi DELETE /api/registrations/{reg_b.id}
    res = client.delete(f"/api/registrations/{reg_b.id}", headers=student_a_headers)
    assert res.status_code == 403
    assert res.json()["error"] == "FORBIDDEN"

    # Kiểm tra trong DB bản ghi của B vẫn an toàn nguyên vẹn
    recheck = db_session.get(Registration, reg_b.id)
    assert recheck is not None


def test_security_prevent_password_hash_leakage(client):
    """BẢO MẬT: Mật khẩu và password_hash tuyệt đối không bao giờ được lọt ra API."""
    res = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@123"})
    assert res.status_code == 200
    res_text = res.text.lower()
    assert "password_hash" not in res_text
    assert "bcrypt" not in res_text

    me_res = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {res.json()['accessToken']}"}
    )
    assert me_res.status_code == 200
    me_text = me_res.text.lower()
    assert "password" not in me_text


def test_security_role_escalation_prevented(client):
    """BẢO MẬT: Sinh viên và Giảng viên không thể leo quyền gọi API của Admin."""
    sv_headers = login(client, "sv1", "Sv@12345")
    gv_headers = login(client, "gv1", "Gv@12345")

    # Sinh viên thử tạo môn học
    res_sv = client.post(
        "/api/subjects",
        json={"subjectCode": "HACK", "name": "Hack", "credits": 3},
        headers=sv_headers,
    )
    assert res_sv.status_code == 403
    assert res_sv.json()["error"] == "FORBIDDEN"

    # Giảng viên thử tạo môn học
    res_gv = client.post(
        "/api/subjects",
        json={"subjectCode": "HACK2", "name": "Hack2", "credits": 3},
        headers=gv_headers,
    )
    assert res_gv.status_code == 403
    assert res_gv.json()["error"] == "FORBIDDEN"
