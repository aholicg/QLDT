from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.entity.auth.lecturer import Lecturer
from app.entity.auth.student import Student
from app.entity.auth.user import Role, User
from app.entity.catalog.course_section import CourseSection
from app.entity.catalog.room import Room
from app.entity.catalog.semester import Semester
from app.entity.catalog.subject import Subject
from app.entity.registration.registration import Registration
from app.entity.tuition.receipt import Receipt
from app.entity.tuition.tuition_discount import TuitionDiscount
from app.entity.tuition.tuition_installment import TuitionInstallment
from app.entity.tuition.tuition_payment import TuitionPayment
from app.entity.tuition.tuition_rate import TuitionRate
from app.security.password import hash_password
from tests.conftest import login


def _tuition_world(db_session):
    semester = Semester(
        semester_code="2026.1",
        name="Học kỳ kiểm thử",
        start_date=date(2026, 9, 7),
        end_date=date(2027, 1, 18),
        num_weeks=20,
    )
    student = db_session.scalars(select(Student)).one()
    student.cohort = "K66"
    student.major = "CNTT"
    lecturer = db_session.scalars(select(Lecturer)).one()
    room = Room(room_code="TUITION-101", capacity=40)
    subject = Subject(
        subject_code="TUI101",
        name="Môn học học phí",
        credits=3,
        tuition_credits=Decimal("1.5"),
    )
    db_session.add_all([semester, room, subject])
    db_session.flush()

    section = CourseSection(
        section_code="TUI-01",
        subject_id=subject.id,
        semester_id=semester.id,
        lecturer_id=lecturer.id,
        room_id=room.id,
        day_of_week=2,
        start_period=1,
        end_period=2,
        start_week=1,
        end_week=20,
        max_capacity=40,
        current_enrollment=1,
    )
    rate = TuitionRate(
        semester_id=semester.id,
        cohort="K66",
        major="CNTT",
        effective_from=semester.start_date,
        effective_to=semester.end_date,
        price_per_credit=10000,
    )
    first_installment = TuitionInstallment(
        semester_id=semester.id,
        installment_order=1,
        name="Đợt 1",
        due_date=date(2026, 10, 1),
        percentage=Decimal("50"),
    )
    second_installment = TuitionInstallment(
        semester_id=semester.id,
        installment_order=2,
        name="Đợt 2",
        due_date=date(2026, 12, 1),
        percentage=Decimal("50"),
    )
    db_session.add_all([section, rate, first_installment, second_installment])
    db_session.flush()
    db_session.add(Registration(student_id=student.id, section_id=section.id))
    db_session.commit()
    return {
        "semester": semester,
        "student": student,
        "rate": rate,
        "subject": subject,
        "first_installment": first_installment,
        "second_installment": second_installment,
    }


def test_student_payment_is_idempotent_and_receipt_pdf_is_available(client, db_session):
    world = _tuition_world(db_session)
    student_headers = login(client, "sv1", "Sv@12345")
    invoice_response = client.get(
        f"/api/tuition/me?semesterId={world['semester'].id}", headers=student_headers
    )
    assert invoice_response.status_code == 200
    assert invoice_response.json()["totalTuition"] == 15000
    assert invoice_response.json()["items"][0]["tuitionCredits"] == 1.5

    payment_body = {
        "installmentId": world["first_installment"].id,
        "amount": 7500,
        "idempotencyKey": "tuition-payment-key-1",
    }
    payment_response = client.post(
        "/api/tuition/me/payments", json=payment_body, headers=student_headers
    )
    assert payment_response.status_code == 201, payment_response.text
    receipt = payment_response.json()
    repeated = client.post("/api/tuition/me/payments", json=payment_body, headers=student_headers)
    assert repeated.status_code == 201
    assert repeated.json()["id"] == receipt["id"]
    assert repeated.json()["receiptNo"] == receipt["receiptNo"]

    pdf_response = client.get(f"/api/receipts/{receipt['id']}/pdf", headers=student_headers)
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert receipt["receiptNo"].encode() in pdf_response.content
    assert pdf_response.content.startswith(b"%PDF-")
    assert "filename*=UTF-8''" in pdf_response.headers["content-disposition"]
    assert db_session.scalar(select(func.count(TuitionPayment.id))) == 1
    assert db_session.scalar(select(func.count(Receipt.id))) == 1
    receipts = client.get(
        f"/api/receipts/me?semesterId={world['semester'].id}", headers=student_headers
    )
    assert receipts.status_code == 200
    assert [item["id"] for item in receipts.json()["items"]] == [receipt["id"]]


def test_tuition_permissions_and_payment_limits(client, db_session):
    world = _tuition_world(db_session)
    student_headers = login(client, "sv1", "Sv@12345")
    admin_headers = login(client, "admin", "Admin@123")
    lecturer_headers = login(client, "gv1", "Gv@12345")

    invoice = client.get(
        f"/api/tuition/me?semesterId={world['semester'].id}", headers=student_headers
    ).json()
    excessive = client.post(
        "/api/tuition/me/payments",
        json={"amount": invoice["balance"] + 1, "idempotencyKey": "too-much"},
        headers=student_headers,
    )
    assert excessive.status_code == 409
    assert excessive.json()["error"] == "PAYMENT_EXCEEDS_BALANCE"

    paid = client.post(
        "/api/tuition/me/payments",
        json={"amount": invoice["balance"], "idempotencyKey": "pay-full"},
        headers=student_headers,
    )
    assert paid.status_code == 201
    after_paid = client.post(
        "/api/tuition/me/payments",
        json={"amount": 1, "idempotencyKey": "pay-again"},
        headers=student_headers,
    )
    assert after_paid.status_code == 409
    assert after_paid.json()["error"] == "INVOICE_ALREADY_PAID"

    student2_user = User(
        username="sv2",
        password_hash=hash_password("Sv2@12345"),
        full_name="Sinh viên thứ hai",
        role=Role.STUDENT,
    )
    db_session.add(student2_user)
    db_session.flush()
    student2 = Student(user_id=student2_user.id, student_code="20210002")
    db_session.add(student2)
    db_session.commit()
    student2_headers = login(client, "sv2", "Sv2@12345")
    foreign_receipt = client.get(f"/api/receipts/{paid.json()['id']}", headers=student2_headers)
    assert foreign_receipt.status_code == 403
    assert (
        client.get(f"/api/receipts/{paid.json()['id']}", headers=lecturer_headers).status_code
        == 403
    )
    assert (
        client.get(f"/api/receipts/{paid.json()['id']}", headers=student_headers).status_code == 200
    )
    assert (
        client.get("/api/admin/tuition/invoices?semesterId=1", headers=lecturer_headers).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/admin/tuition/invoices?semesterId={world['semester'].id}",
            headers=admin_headers,
        ).status_code
        == 200
    )


def test_discount_excess_rejected_and_installment_reconfiguration_after_payment_blocked(
    client, db_session
):
    world = _tuition_world(db_session)
    admin_headers = login(client, "admin", "Admin@123")
    student_headers = login(client, "sv1", "Sv@12345")

    db_session.add(
        TuitionDiscount(
            student_id=world["student"].id,
            semester_id=world["semester"].id,
            discount_percent=Decimal("50"),
            fixed_amount=10000,
            reason="Kiểm thử vượt tổng",
            granted_by="admin",
        )
    )
    db_session.commit()
    result = client.post(
        "/api/admin/tuition/invoices/generate",
        json={"semesterId": world["semester"].id, "studentId": world["student"].id},
        headers=admin_headers,
    )
    assert result.status_code == 400
    assert result.json()["error"] == "DISCOUNT_EXCEEDS_TOTAL"

    db_session.query(TuitionDiscount).delete()
    db_session.commit()
    invoice = client.get(
        f"/api/tuition/me?semesterId={world['semester'].id}", headers=student_headers
    ).json()
    payment = client.post(
        "/api/tuition/me/payments",
        json={"amount": invoice["balance"], "idempotencyKey": "paid-before-reconfigure"},
        headers=student_headers,
    )
    assert payment.status_code == 201
    reconfigure = client.put(
        "/api/admin/tuition/installments",
        json={
            "semesterId": world["semester"].id,
            "installments": [
                {
                    "installmentOrder": 1,
                    "name": "Đợt duy nhất",
                    "dueDate": "2026-12-01",
                    "percentage": 100,
                }
            ],
        },
        headers=admin_headers,
    )
    assert reconfigure.status_code == 409
    assert reconfigure.json()["error"] == "INVOICE_HAS_PAYMENTS"


def test_admin_tuition_configuration_generation_and_reporting(client, db_session):
    world = _tuition_world(db_session)
    admin_headers = login(client, "admin", "Admin@123")

    rates = client.get(
        f"/api/admin/tuition-rates?semesterId={world['semester'].id}",
        headers=admin_headers,
    )
    assert rates.status_code == 200
    assert rates.json()["items"][0]["effectiveFrom"] == "2026-09-07"

    duplicate_rate = client.post(
        "/api/admin/tuition-rates",
        headers=admin_headers,
        json={
            "semesterId": world["semester"].id,
            "cohort": "K66",
            "major": "CNTT",
            "pricePerCredit": 12000,
        },
    )
    assert duplicate_rate.status_code == 409
    assert duplicate_rate.json()["error"] == "DUPLICATE_CODE"

    discount = client.post(
        "/api/admin/tuition/discounts",
        headers=admin_headers,
        json={
            "studentId": world["student"].id,
            "semesterId": world["semester"].id,
            "discountPercent": 10,
            "reason": "Hỗ trợ kiểm thử",
        },
    )
    assert discount.status_code == 201, discount.text
    assert discount.json()["discountPercent"] == 10.0
    admin_name = db_session.scalars(select(User).where(User.username == "admin")).one().full_name
    assert discount.json()["grantedBy"] == admin_name

    duplicate_installments = client.put(
        "/api/admin/tuition/installments",
        headers=admin_headers,
        json={
            "semesterId": world["semester"].id,
            "installments": [
                {
                    "installmentOrder": 1,
                    "name": "Đợt A",
                    "dueDate": "2026-10-01",
                    "percentage": 50,
                },
                {
                    "installmentOrder": 1,
                    "name": "Đợt B",
                    "dueDate": "2026-12-01",
                    "percentage": 50,
                },
            ],
        },
    )
    assert duplicate_installments.status_code == 400
    assert duplicate_installments.json()["error"] == "INSTALLMENT_SUM_MISMATCH"

    generated = client.post(
        "/api/admin/tuition/invoices/generate",
        headers=admin_headers,
        json={"semesterId": world["semester"].id, "studentId": world["student"].id},
    )
    assert generated.status_code == 200, generated.text
    assert generated.json()["totalGenerated"] == 1

    invoices = client.get(
        f"/api/admin/tuition/invoices?semesterId={world['semester'].id}&page=1&size=10",
        headers=admin_headers,
    )
    assert invoices.status_code == 200
    assert invoices.json()["items"][0]["amountDue"] == 13500
    summary = client.get(
        f"/api/admin/tuition/reports/summary?semesterId={world['semester'].id}",
        headers=admin_headers,
    )
    assert summary.status_code == 200
    assert summary.json()["totalInvoices"] == 1
    assert summary.json()["totalAmountDue"] == 13500


def test_student_tuition_rejects_unknown_semester(client):
    student_headers = login(client, "sv1", "Sv@12345")
    response = client.get("/api/tuition/me?semesterId=999999", headers=student_headers)
    assert response.status_code == 404


def test_student_tuition_requires_a_rate_when_registered(client, db_session):
    world = _tuition_world(db_session)
    db_session.delete(world["rate"])
    db_session.commit()

    student_headers = login(client, "sv1", "Sv@12345")
    response = client.get(
        f"/api/tuition/me?semesterId={world['semester'].id}", headers=student_headers
    )
    assert response.status_code == 404
    assert response.json()["error"] == "TUITION_RATE_NOT_FOUND"
