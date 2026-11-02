from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.error_codes import ErrorCode
from app.core.exceptions import AppError, field_error
from app.core.timeutil import now_vn, to_vn, today_vn
from app.dto.common import Page, PageParams
from app.dto.tuition.tuition import (
    InvoiceGenerateRequest,
    InvoiceGenerateResult,
    PaymentCreateRequest,
    ReceiptDto,
    TuitionDiscountCreateRequest,
    TuitionDiscountResponse,
    TuitionInstallmentResponse,
    TuitionInstallmentsPutRequest,
    TuitionInvoiceDto,
    TuitionInvoiceItemDto,
    TuitionPaymentDto,
    TuitionRateCreateRequest,
    TuitionRateResponse,
    TuitionRateUpdateRequest,
    TuitionSummaryDto,
)
from app.entity.auth.student import Student
from app.entity.auth.user import Role, User
from app.entity.catalog.semester import Semester
from app.entity.catalog.subject import Subject
from app.entity.tuition.receipt import Receipt
from app.entity.tuition.tuition_discount import TuitionDiscount
from app.entity.tuition.tuition_installment import TuitionInstallment
from app.entity.tuition.tuition_invoice import InvoiceStatus, TuitionInvoice
from app.entity.tuition.tuition_invoice_item import TuitionInvoiceItem
from app.entity.tuition.tuition_payment import TuitionPayment
from app.entity.tuition.tuition_rate import TuitionRate
from app.repository.auth.user_repository import StudentRepository
from app.repository.catalog.semester_repository import SemesterRepository
from app.repository.tuition.tuition_repository import TuitionRepository
from app.service.catalog.semester_service import SemesterService
from app.service.tuition.tuition_calculator import (
    calculate_discount,
    calculate_installments,
    calculate_subject_tuition,
    resolve_tuition_rate,
)
from app.service.tuition.vietnamese_words import number_to_vietnamese_words


class TuitionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = TuitionRepository(db)
        self.students = StudentRepository(db)
        self.semesters = SemesterRepository(db)

    def _ensure_rate_range_available(
        self,
        semester_id: int,
        cohort: str | None,
        major: str | None,
        effective_from: date,
        effective_to: date | None,
        exclude_rate_id: int | None = None,
    ) -> None:
        self.repo.lock_semester(semester_id)
        if effective_to is not None and effective_to < effective_from:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                details=[field_error("effectiveTo", "Ngày kết thúc phải sau ngày bắt đầu")],
            )
        for rate in self.repo.list_rates(semester_id):
            if rate.id == exclude_rate_id or rate.cohort != cohort or rate.major != major:
                continue
            overlaps = (rate.effective_to is None or effective_from <= rate.effective_to) and (
                effective_to is None or rate.effective_from <= effective_to
            )
            if overlaps:
                raise AppError(
                    ErrorCode.DUPLICATE_CODE,
                    details=[
                        field_error(
                            "effectiveFrom",
                            "Khoảng hiệu lực bị trùng với đơn giá cùng học kỳ, khóa và ngành",
                        )
                    ],
                )

    # ==================== TUITION RATES ====================
    def list_rates(self, semester_id: int | None = None) -> list[TuitionRateResponse]:
        entities = self.repo.list_rates(semester_id)
        return [
            TuitionRateResponse(
                id=r.id,
                semester_id=r.semester_id,
                cohort=r.cohort,
                major=r.major,
                effective_from=r.effective_from,
                effective_to=r.effective_to,
                price_per_credit=r.price_per_credit,
                description=r.description,
                created_at=to_vn(r.created_at),
            )
            for r in entities
        ]

    def create_rate(self, request: TuitionRateCreateRequest) -> TuitionRateResponse:
        semester = self.semesters.get_by_id(request.semester_id)
        if semester is None:
            raise AppError(
                ErrorCode.NOT_FOUND, details=[field_error("semesterId", "Học kỳ không tồn tại")]
            )

        effective_from = request.effective_from or semester.start_date
        effective_to = request.effective_to or semester.end_date
        self._ensure_rate_range_available(
            request.semester_id,
            request.cohort,
            request.major,
            effective_from,
            effective_to,
        )
        self.repo.mark_invoices_stale(request.semester_id)
        entity = TuitionRate(
            semester_id=request.semester_id,
            cohort=request.cohort,
            major=request.major,
            effective_from=effective_from,
            effective_to=effective_to,
            price_per_credit=request.price_per_credit,
            description=request.description,
        )
        self.repo.add_rate(entity)
        self.db.commit()
        return TuitionRateResponse(
            id=entity.id,
            semester_id=entity.semester_id,
            cohort=entity.cohort,
            major=entity.major,
            effective_from=entity.effective_from,
            effective_to=entity.effective_to,
            price_per_credit=entity.price_per_credit,
            description=entity.description,
            created_at=to_vn(entity.created_at),
        )

    def update_rate(self, rate_id: int, request: TuitionRateUpdateRequest) -> TuitionRateResponse:
        entity = self.repo.get_rate_by_id(rate_id)
        if entity is None:
            raise AppError(ErrorCode.NOT_FOUND)

        effective_from = request.effective_from or entity.effective_from
        effective_to = (
            request.effective_to
            if "effective_to" in request.model_fields_set
            else entity.effective_to
        )
        self._ensure_rate_range_available(
            entity.semester_id,
            request.cohort,
            request.major,
            effective_from,
            effective_to,
            exclude_rate_id=entity.id,
        )
        self.repo.mark_invoices_stale(entity.semester_id)
        entity.cohort = request.cohort
        entity.major = request.major
        entity.effective_from = effective_from
        entity.effective_to = effective_to
        entity.price_per_credit = request.price_per_credit
        entity.description = request.description
        self.db.commit()
        return TuitionRateResponse(
            id=entity.id,
            semester_id=entity.semester_id,
            cohort=entity.cohort,
            major=entity.major,
            effective_from=entity.effective_from,
            effective_to=entity.effective_to,
            price_per_credit=entity.price_per_credit,
            description=entity.description,
            created_at=to_vn(entity.created_at),
        )

    def delete_rate(self, rate_id: int) -> None:
        entity = self.repo.get_rate_by_id(rate_id)
        if entity is None:
            raise AppError(ErrorCode.NOT_FOUND)
        self.repo.mark_invoices_stale(entity.semester_id)
        self.repo.delete_rate(entity)
        self.db.commit()

    # ==================== TUITION DISCOUNTS ====================
    def list_discounts(
        self, semester_id: int | None = None, student_id: int | None = None
    ) -> list[TuitionDiscountResponse]:
        entities = self.repo.list_discounts(semester_id, student_id)
        return [
            TuitionDiscountResponse(
                id=d.id,
                student_id=d.student_id,
                student_code=d.student.student_code if d.student else None,
                student_name=d.student.full_name if d.student else None,
                semester_id=d.semester_id,
                discount_percent=d.discount_percent,
                fixed_amount=d.fixed_amount,
                reason=d.reason,
                granted_by=d.granted_by,
                created_at=to_vn(d.created_at),
            )
            for d in entities
        ]

    def create_discount(
        self, request: TuitionDiscountCreateRequest, granted_by: str
    ) -> TuitionDiscountResponse:
        student: Student | None = None
        if request.student_id is not None:
            student = self.students.get_by_id(request.student_id)
        elif request.student_code:
            student = self.students.get_by_code(request.student_code)

        if student is None:
            raise AppError(
                ErrorCode.NOT_FOUND, details=[field_error("studentId", "Sinh viên không tồn tại")]
            )

        semester = self.semesters.get_by_id(request.semester_id)
        if semester is None:
            raise AppError(
                ErrorCode.NOT_FOUND, details=[field_error("semesterId", "Học kỳ không tồn tại")]
            )

        entity = TuitionDiscount(
            student_id=student.id,
            semester_id=request.semester_id,
            discount_percent=request.discount_percent,
            fixed_amount=request.fixed_amount,
            reason=request.reason,
            granted_by=granted_by,
        )
        self.repo.add_discount(entity)
        self.repo.mark_invoices_stale(request.semester_id, student.id)
        self.db.commit()
        return TuitionDiscountResponse(
            id=entity.id,
            student_id=entity.student_id,
            student_code=student.student_code,
            student_name=student.full_name,
            semester_id=entity.semester_id,
            discount_percent=entity.discount_percent,
            fixed_amount=entity.fixed_amount,
            reason=entity.reason,
            granted_by=entity.granted_by,
            created_at=to_vn(entity.created_at),
        )

    def delete_discount(self, discount_id: int) -> None:
        entity = self.repo.get_discount_by_id(discount_id)
        if entity is None:
            raise AppError(ErrorCode.NOT_FOUND)
        self.repo.mark_invoices_stale(entity.semester_id, entity.student_id)
        self.repo.delete_discount(entity)
        self.db.commit()

    # ==================== TUITION INSTALLMENTS ====================
    def list_installments(self, semester_id: int) -> list[TuitionInstallmentResponse]:
        entities = self.repo.list_installments(semester_id)
        return [
            TuitionInstallmentResponse(
                id=inst.id,
                semester_id=inst.semester_id,
                installment_order=inst.installment_order,
                name=inst.name,
                due_date=inst.due_date,
                percentage=inst.percentage,
                fixed_amount=inst.fixed_amount,
            )
            for inst in entities
        ]

    def configure_installments(
        self, request: TuitionInstallmentsPutRequest
    ) -> list[TuitionInstallmentResponse]:
        semester = self.semesters.get_by_id(request.semester_id)
        if semester is None:
            raise AppError(
                ErrorCode.NOT_FOUND, details=[field_error("semesterId", "Học kỳ không tồn tại")]
            )

        if self.repo.has_payments_for_semester(request.semester_id):
            raise AppError(ErrorCode.INVOICE_HAS_PAYMENTS)

        installment_orders = [item.installment_order for item in request.installments]
        if len(installment_orders) != len(set(installment_orders)):
            raise AppError(
                ErrorCode.INSTALLMENT_SUM_MISMATCH,
                details=[field_error("installments", "Thứ tự các đợt nộp không được trùng")],
            )

        # Kiểm tra tổng % nếu toàn bộ là %
        has_percentage = [i.percentage for i in request.installments if i.percentage is not None]
        has_fixed = [i.fixed_amount for i in request.installments if i.fixed_amount is not None]
        if has_percentage and has_fixed:
            raise AppError(
                ErrorCode.INSTALLMENT_SUM_MISMATCH,
                details=[
                    field_error(
                        "installments",
                        "Các đợt trong cùng học kỳ phải dùng thống nhất tỷ lệ hoặc số tiền cố định",
                    )
                ],
            )
        if len(has_percentage) == len(request.installments) and len(request.installments) > 0:
            total_pct = sum(has_percentage)
            if total_pct != Decimal("100.00"):
                raise AppError(
                    ErrorCode.INSTALLMENT_SUM_MISMATCH,
                    details=[
                        field_error(
                            "installments",
                            f"Tổng tỷ lệ phần trăm các đợt phải bằng 100% (hiện tại: {total_pct}%)",
                        )
                    ],
                )

        new_entities = [
            TuitionInstallment(
                semester_id=request.semester_id,
                installment_order=i.installment_order,
                name=i.name,
                due_date=i.due_date,
                percentage=i.percentage,
                fixed_amount=i.fixed_amount,
            )
            for i in request.installments
        ]
        self.repo.replace_installments(request.semester_id, new_entities)
        self.db.commit()
        return self.list_installments(request.semester_id)

    # ==================== INVOICE CALCULATION / GENERATION ====================
    def generate_single_invoice(
        self,
        student: Student,
        semester: Semester,
        rates: list[TuitionRate],
        registered_subjects: list[Subject],
    ) -> TuitionInvoice | None:
        """Tạo mới hoặc tính lại hóa đơn cho một sinh viên."""
        existing = self.repo.get_invoice_by_student_semester_for_update(student.id, semester.id)
        if existing and (existing.amount_paid > 0 or existing.status == InvoiceStatus.CANCELLED):
            return None  # Không tính lại hóa đơn đã có giao dịch nộp tiền

        items_to_add, total_tuition = self._build_invoice_items(
            student, semester, rates, registered_subjects
        )
        total_discount, amount_due = self._calculate_discount(
            total_tuition, self.repo.list_discounts(semester.id, student.id)
        )

        if existing is None:
            invoice = TuitionInvoice(
                student_id=student.id,
                semester_id=semester.id,
                total_tuition=total_tuition,
                total_discount=total_discount,
                amount_due=amount_due,
                amount_paid=0,
                status=InvoiceStatus.UNPAID,
                is_stale=False,
                items=items_to_add,
            )
            self.repo.add_invoice(invoice)
        else:
            existing.total_tuition = total_tuition
            existing.total_discount = total_discount
            existing.amount_due = amount_due
            existing.is_stale = False
            self.repo.delete_invoice_items(existing.id)
            existing.items = items_to_add
            invoice = existing

        return invoice

    @staticmethod
    def _build_invoice_items(
        student: Student,
        semester: Semester,
        rates: list[TuitionRate],
        registered_subjects: list[Subject],
    ) -> tuple[list[TuitionInvoiceItem], int]:
        rate = resolve_tuition_rate(
            rates, student.cohort, student.major, effective_date=semester.start_date
        )
        if registered_subjects and rate is None:
            raise AppError(
                ErrorCode.TUITION_RATE_NOT_FOUND,
                message=f"Chưa có đơn giá học phí cho học kỳ {semester.semester_code}",
            )

        items: list[TuitionInvoiceItem] = []
        total = 0
        if rate is not None:
            for subject in registered_subjects:
                amount = calculate_subject_tuition(
                    subject.effective_tuition_credits, rate.price_per_credit
                )
                total += amount
                items.append(
                    TuitionInvoiceItem(
                        subject_id=subject.id,
                        subject_code=subject.subject_code,
                        subject_name=subject.name,
                        credits=subject.credits,
                        tuition_credits=subject.effective_tuition_credits,
                        price_per_credit=rate.price_per_credit,
                        amount=amount,
                    )
                )
        return items, total

    @staticmethod
    def _calculate_discount(
        total_tuition: int, discounts: list[TuitionDiscount]
    ) -> tuple[int, int]:
        percent = sum((discount.discount_percent for discount in discounts), Decimal("0"))
        fixed_amount = sum(discount.fixed_amount for discount in discounts)
        percent_discount = int(Decimal(total_tuition) * percent / Decimal("100"))
        total_discount = percent_discount + fixed_amount
        if total_discount > total_tuition:
            raise AppError(
                ErrorCode.DISCOUNT_EXCEEDS_TOTAL,
                details=[
                    field_error(
                        "discounts",
                        "Tổng miễn giảm phần trăm và số tiền cố định vượt quá tổng học phí",
                    )
                ],
            )
        return calculate_discount(total_tuition, percent, fixed_amount)

    def generate_invoices(self, request: InvoiceGenerateRequest) -> InvoiceGenerateResult:
        """Tạo/tính lại hóa đơn hàng loạt bằng truy vấn gom nhóm tránh N+1."""
        semester = self.semesters.get_by_id(request.semester_id)
        if semester is None:
            raise AppError(
                ErrorCode.NOT_FOUND, details=[field_error("semesterId", "Học kỳ không tồn tại")]
            )

        rates = self.repo.list_rates(request.semester_id)
        if not rates and not request.student_id:
            raise AppError(
                ErrorCode.TUITION_RATE_NOT_FOUND,
                message=f"Chưa có bảng đơn giá học phí cho học kỳ {semester.semester_code}",
            )

        students = self.repo.list_students_for_update(request.student_id)
        if request.student_id is not None and not students:
            raise AppError(ErrorCode.NOT_FOUND)
        student_ids = [student.id for student in students]
        student_subjects_map = self.repo.get_registered_students_and_subjects(
            request.semester_id, student_id=request.student_id
        )
        discounts_by_student = self.repo.list_discounts_by_students(
            request.semester_id, student_ids
        )
        existing_by_student = {
            invoice.student_id: invoice
            for invoice in self.repo.list_invoices_for_students_for_update(
                request.semester_id, student_ids
            )
        }
        total_generated = 0
        total_skipped = 0
        invoices_to_add: list[TuitionInvoice] = []
        invoices_to_update: list[TuitionInvoice] = []
        invoice_items_to_add: list[tuple[TuitionInvoice, list[TuitionInvoiceItem]]] = []

        for student in students:
            subjects = student_subjects_map.get(student.id, [])
            items, total_tuition = self._build_invoice_items(student, semester, rates, subjects)
            total_discount, amount_due = self._calculate_discount(
                total_tuition, discounts_by_student.get(student.id, [])
            )
            existing = existing_by_student.get(student.id)
            if existing and (
                existing.amount_paid > 0 or existing.status == InvoiceStatus.CANCELLED
            ):
                total_skipped += 1
                continue
            if existing is None:
                invoice = TuitionInvoice(
                    student_id=student.id,
                    semester_id=semester.id,
                    total_tuition=total_tuition,
                    total_discount=total_discount,
                    amount_due=amount_due,
                    amount_paid=0,
                    status=InvoiceStatus.UNPAID,
                    is_stale=False,
                )
                invoices_to_add.append(invoice)
            else:
                invoice = existing
                invoice.total_tuition = total_tuition
                invoice.total_discount = total_discount
                invoice.amount_due = amount_due
                invoice.is_stale = False
                invoices_to_update.append(invoice)
            invoice_items_to_add.append((invoice, items))
            total_generated += 1

        self.repo.delete_invoice_items_for_invoices([item.id for item in invoices_to_update])
        self.db.add_all(invoices_to_add)
        self.db.add_all(invoices_to_update)
        self.db.flush()
        for invoice, items in invoice_items_to_add:
            for item in items:
                item.invoice_id = invoice.id
        self.db.add_all(item for _, items in invoice_items_to_add for item in items)

        self.db.commit()
        return InvoiceGenerateResult(
            total_generated=total_generated,
            total_skipped=total_skipped,
            message=f"Đã tạo/cập nhật {total_generated} hóa đơn ({total_skipped} hóa đơn bỏ qua do đã nộp tiền)",
        )

    # ==================== STUDENT TUITION VIEW ====================
    def get_student_tuition(self, user: User, semester_id: int | None = None) -> TuitionInvoiceDto:
        student = self.students.get_by_user_id(user.id)
        if student is None:
            raise AppError(ErrorCode.FORBIDDEN)

        if semester_id is None:
            semester_id = SemesterService(self.db).get_current().id

        invoice = self.repo.get_invoice(student.id, semester_id)
        semester = self.semesters.get_by_id(semester_id)
        if semester is None:
            raise AppError(
                ErrorCode.NOT_FOUND, details=[field_error("semesterId", "Học kỳ không tồn tại")]
            )

        # Nếu chưa có hóa đơn nhưng sinh viên đã đăng ký môn, thử sinh tự động
        if invoice is None:
            subj_map = self.repo.get_registered_students_and_subjects(semester_id, student.id)
            subjects = subj_map.get(student.id, [])
            if subjects:
                rates = self.repo.list_rates(semester_id)
                if not rates:
                    raise AppError(ErrorCode.TUITION_RATE_NOT_FOUND)
                self.generate_single_invoice(student, semester, rates, subjects)
                self.db.commit()
                invoice = self.repo.get_invoice(student.id, semester_id)

        if invoice is None:
            # Trả về DTO rỗng trạng thái UNPAID
            return TuitionInvoiceDto(
                id=0,
                student_id=student.id,
                student_code=student.student_code,
                student_name=student.full_name,
                cohort=student.cohort,
                major=student.major,
                semester_id=semester_id,
                semester_code=semester.semester_code,
                total_tuition=0,
                total_discount=0,
                amount_due=0,
                amount_paid=0,
                balance=0,
                status="UNPAID",
                is_stale=False,
                items=[],
                discounts=[],
                installments=[],
                payments=[],
                created_at=now_vn(),
                updated_at=now_vn(),
            )

        # Tính đợt nộp và trạng thái
        installments = self.repo.list_installments(semester_id)
        inst_specs = [
            {
                "id": inst.id,
                "semesterId": inst.semester_id,
                "installmentOrder": inst.installment_order,
                "name": inst.name,
                "dueDate": inst.due_date,
                "percentage": inst.percentage,
                "fixedAmount": inst.fixed_amount,
            }
            for inst in installments
        ]
        try:
            calculated_insts = calculate_installments(invoice.amount_due, inst_specs)
        except ValueError as exc:
            raise AppError(
                ErrorCode.INSTALLMENT_SUM_MISMATCH,
                details=[field_error("installments", str(exc))],
            ) from exc

        today = today_vn()
        lump_sum_paid = sum(
            payment.amount for payment in invoice.payments if payment.installment_id is None
        )
        direct_paid = {
            installment.id: sum(
                payment.amount
                for payment in invoice.payments
                if payment.installment_id == installment.id
            )
            for installment in installments
        }
        installment_dtos: list[TuitionInstallmentResponse] = []
        for c in calculated_insts:
            alloc = c["allocatedAmount"]
            paid_for_installment = direct_paid.get(c["id"], 0)
            extra = min(lump_sum_paid, max(0, alloc - paid_for_installment))
            lump_sum_paid -= extra
            if paid_for_installment + extra >= alloc:
                status = "PAID"
            elif c["dueDate"] < today:
                status = "OVERDUE"
            else:
                status = "PENDING"

            installment_dtos.append(
                TuitionInstallmentResponse(
                    id=c["id"],
                    semester_id=c["semesterId"],
                    installment_order=c["installmentOrder"],
                    name=c["name"],
                    due_date=c["dueDate"],
                    percentage=c["percentage"],
                    fixed_amount=c["fixedAmount"],
                    allocated_amount=alloc,
                    status=status,
                )
            )

        discounts = self.repo.list_discounts(semester_id, student.id)
        discount_dtos = [
            TuitionDiscountResponse(
                id=d.id,
                student_id=d.student_id,
                student_code=student.student_code,
                student_name=student.full_name,
                semester_id=d.semester_id,
                discount_percent=d.discount_percent,
                fixed_amount=d.fixed_amount,
                reason=d.reason,
                granted_by=d.granted_by,
                created_at=to_vn(d.created_at),
            )
            for d in discounts
        ]

        items_dtos = [
            TuitionInvoiceItemDto(
                id=item.id,
                subject_id=item.subject_id,
                subject_code=item.subject_code,
                subject_name=item.subject_name,
                credits=item.credits,
                tuition_credits=item.tuition_credits,
                price_per_credit=item.price_per_credit,
                amount=item.amount,
            )
            for item in invoice.items
        ]

        payments_dtos = [
            TuitionPaymentDto(
                id=p.id,
                amount=p.amount,
                idempotency_key=p.idempotency_key,
                payment_method=p.payment_method,
                paid_at=to_vn(p.paid_at),
                receipt_no=p.receipt.receipt_no if p.receipt else None,
            )
            for p in invoice.payments
        ]

        balance = max(0, invoice.amount_due - invoice.amount_paid)
        return TuitionInvoiceDto(
            id=invoice.id,
            student_id=student.id,
            student_code=student.student_code,
            student_name=student.full_name,
            cohort=student.cohort,
            major=student.major,
            semester_id=invoice.semester_id,
            semester_code=invoice.semester.semester_code if invoice.semester else "",
            total_tuition=invoice.total_tuition,
            total_discount=invoice.total_discount,
            amount_due=invoice.amount_due,
            amount_paid=invoice.amount_paid,
            balance=balance,
            status=invoice.status.value,
            is_stale=invoice.is_stale,
            items=items_dtos,
            discounts=discount_dtos,
            installments=installment_dtos,
            payments=payments_dtos,
            created_at=to_vn(invoice.created_at),
            updated_at=to_vn(invoice.updated_at),
        )

    # ==================== IDEMPOTENT PAYMENT ====================
    def make_payment(self, user: User, request: PaymentCreateRequest) -> ReceiptDto:
        """Thực hiện thanh toán giả lập học phí idempotent và phát hành biên lai bất biến."""
        student = self.students.get_by_user_id(user.id)
        if student is None:
            raise AppError(ErrorCode.FORBIDDEN)

        # 1. Kiểm tra idempotency key trước
        existing_payment = self.repo.get_payment_by_key(student.id, request.idempotency_key)
        if existing_payment and existing_payment.receipt:
            return self._receipt_dto(existing_payment.receipt, student)

        semester_id = SemesterService(self.db).get_current().id

        # 2. Khóa dòng hóa đơn FOR UPDATE
        invoice = self.repo.get_invoice_by_student_semester_for_update(student.id, semester_id)
        if invoice is None:
            raise AppError(ErrorCode.INVOICE_NOT_FOUND)

        existing_payment = self.repo.get_payment_by_key(student.id, request.idempotency_key)
        if existing_payment and existing_payment.receipt:
            return self._receipt_dto(existing_payment.receipt, student)

        if invoice.status == InvoiceStatus.PAID:
            raise AppError(ErrorCode.INVOICE_ALREADY_PAID)
        if invoice.status == InvoiceStatus.CANCELLED:
            raise AppError(ErrorCode.INVOICE_CANCELLED)

        installment = None
        if request.installment_id is not None:
            installment = self.repo.get_installment_by_id(request.installment_id)
            if installment is None or installment.semester_id != semester_id:
                raise AppError(
                    ErrorCode.VALIDATION_ERROR,
                    details=[field_error("installmentId", "Đợt nộp không thuộc học kỳ hiện tại")],
                )
            installment_specs = [
                {
                    "id": item.id,
                    "percentage": item.percentage,
                    "fixedAmount": item.fixed_amount,
                }
                for item in self.repo.list_installments(semester_id)
            ]
            try:
                installment_allocations = calculate_installments(
                    invoice.amount_due, installment_specs
                )
            except ValueError as exc:
                raise AppError(
                    ErrorCode.INSTALLMENT_SUM_MISMATCH,
                    details=[field_error("installments", str(exc))],
                ) from exc
            allocation = next(
                (
                    item["allocatedAmount"]
                    for item in installment_allocations
                    if item["id"] == installment.id
                ),
                None,
            )
            if allocation is None:
                raise AppError(ErrorCode.VALIDATION_ERROR)
            paid_for_installment = self.repo.paid_amount_for_installment(invoice.id, installment.id)
            if request.amount > allocation - paid_for_installment:
                raise AppError(
                    ErrorCode.PAYMENT_EXCEEDS_BALANCE,
                    details=[
                        field_error(
                            "amount",
                            "Số tiền thanh toán vượt quá số còn thiếu của đợt đã chọn",
                        )
                    ],
                )

        balance = invoice.amount_due - invoice.amount_paid
        if request.amount > balance:
            raise AppError(
                ErrorCode.PAYMENT_EXCEEDS_BALANCE,
                details=[
                    field_error(
                        "amount",
                        f"Số tiền nộp ({request.amount:,} ₫) vượt quá số dư còn thiếu ({balance:,} ₫)",
                    )
                ],
            )

        # 3. Tạo thanh toán
        payment = TuitionPayment(
            invoice_id=invoice.id,
            student_id=student.id,
            installment_id=request.installment_id,
            amount=request.amount,
            idempotency_key=request.idempotency_key,
            payment_method="SIMULATED",
        )
        self.repo.add_payment(payment)

        # 4. Cập nhật số tiền đã nộp và trạng thái hóa đơn
        invoice.amount_paid += request.amount
        if invoice.amount_paid == invoice.amount_due:
            invoice.status = InvoiceStatus.PAID
        else:
            invoice.status = InvoiceStatus.PARTIALLY_PAID

        # 5. Cấp số biên lai tuần tự có khóa dòng
        semester = self.semesters.get_by_id(semester_id)
        semester_code = semester.semester_code if semester else "2026.1"
        receipt_no = self.repo.next_receipt_number(semester_id, semester_code)

        # 6. Tạo snapshot bất biến cho biên lai
        snapshot_items = [
            {
                "subjectCode": item.subject_code,
                "subjectName": item.subject_name,
                "credits": item.credits,
                "tuitionCredits": str(item.tuition_credits),
                "pricePerCredit": item.price_per_credit,
                "amount": item.amount,
            }
            for item in invoice.items
        ]
        receipt_data = {
            "receiptNo": receipt_no,
            "studentCode": student.student_code,
            "fullName": student.full_name,
            "cohort": student.cohort or "",
            "major": student.major or "",
            "semesterCode": semester_code,
            "semesterName": semester.name if semester else "",
            "items": snapshot_items,
            "totalTuition": invoice.total_tuition,
            "totalDiscount": invoice.total_discount,
            "amountDue": invoice.amount_due,
            "paymentAmount": request.amount,
            "cumulativePaid": invoice.amount_paid,
            "balanceRemaining": max(0, invoice.amount_due - invoice.amount_paid),
            "amountInWords": number_to_vietnamese_words(request.amount),
            "paymentMethod": "Thanh toán giả lập",
        }

        receipt = Receipt(
            receipt_no=receipt_no,
            payment=payment,
            student_id=student.id,
            invoice_id=invoice.id,
            amount=request.amount,
            receipt_data=receipt_data,
        )
        self.repo.add_receipt(receipt)
        self.db.commit()

        return self._receipt_dto(receipt, student)

    @staticmethod
    def _receipt_dto(receipt: Receipt, student: Student) -> ReceiptDto:
        return ReceiptDto(
            id=receipt.id,
            receipt_no=receipt.receipt_no,
            payment_id=receipt.payment_id,
            student_id=receipt.student_id,
            student_code=student.student_code,
            student_name=student.full_name,
            invoice_id=receipt.invoice_id,
            amount=receipt.amount,
            amount_in_words=number_to_vietnamese_words(receipt.amount),
            issued_at=to_vn(receipt.issued_at),
            receipt_data=receipt.receipt_data,
        )

    # ==================== RECEIPTS QUERIES ====================
    def list_student_receipts(self, user: User, semester_id: int | None = None) -> list[ReceiptDto]:
        student = self.students.get_by_user_id(user.id)
        if student is None:
            raise AppError(ErrorCode.FORBIDDEN)

        entities = self.repo.list_receipts_by_student(student.id, semester_id)
        return [
            ReceiptDto(
                id=r.id,
                receipt_no=r.receipt_no,
                payment_id=r.payment_id,
                student_id=r.student_id,
                student_code=student.student_code,
                student_name=student.full_name,
                invoice_id=r.invoice_id,
                amount=r.amount,
                amount_in_words=number_to_vietnamese_words(r.amount),
                issued_at=to_vn(r.issued_at),
                receipt_data=r.receipt_data,
            )
            for r in entities
        ]

    def get_receipt(self, user: User, receipt_id: int) -> ReceiptDto:
        receipt = self.repo.get_receipt_by_id(receipt_id)
        if receipt is None:
            raise AppError(ErrorCode.NOT_FOUND)

        if user.role == Role.STUDENT:
            student = self.students.get_by_user_id(user.id)
            if student is None or receipt.student_id != student.id:
                raise AppError(ErrorCode.FORBIDDEN)
        elif user.role != Role.ADMIN:
            raise AppError(ErrorCode.FORBIDDEN)

        return ReceiptDto(
            id=receipt.id,
            receipt_no=receipt.receipt_no,
            payment_id=receipt.payment_id,
            student_id=receipt.student_id,
            student_code=receipt.student.student_code if receipt.student else None,
            student_name=receipt.student.full_name if receipt.student else None,
            invoice_id=receipt.invoice_id,
            amount=receipt.amount,
            amount_in_words=number_to_vietnamese_words(receipt.amount),
            issued_at=to_vn(receipt.issued_at),
            receipt_data=receipt.receipt_data,
        )

    # ==================== ADMIN INVOICES & SUMMARY ====================
    def list_admin_invoices(
        self,
        semester_id: int,
        status: str | None,
        student_code: str | None,
        paging: PageParams,
    ) -> Page[TuitionInvoiceDto]:
        st_enum = InvoiceStatus(status) if status else None
        invoices, total = self.repo.list_invoices(
            semester_id=semester_id,
            status=st_enum,
            student_code=student_code,
            offset=paging.offset,
            limit=paging.size,
        )

        dtos = [
            TuitionInvoiceDto(
                id=inv.id,
                student_id=inv.student_id,
                student_code=inv.student.student_code if inv.student else "",
                student_name=inv.student.full_name if inv.student else "",
                cohort=inv.student.cohort if inv.student else None,
                major=inv.student.major if inv.student else None,
                semester_id=inv.semester_id,
                semester_code=inv.semester.semester_code if inv.semester else "",
                total_tuition=inv.total_tuition,
                total_discount=inv.total_discount,
                amount_due=inv.amount_due,
                amount_paid=inv.amount_paid,
                balance=max(0, inv.amount_due - inv.amount_paid),
                status=inv.status.value,
                is_stale=inv.is_stale,
                items=[],
                discounts=[],
                installments=[],
                payments=[],
                created_at=to_vn(inv.created_at),
                updated_at=to_vn(inv.updated_at),
            )
            for inv in invoices
        ]
        return Page.of(dtos, paging, total)

    def get_summary(self, semester_id: int) -> TuitionSummaryDto:
        semester = self.semesters.get_by_id(semester_id)
        data = self.repo.get_summary(semester_id)
        return TuitionSummaryDto(
            semester_id=semester_id,
            semester_code=semester.semester_code if semester else "",
            total_invoices=data["totalInvoices"],
            total_amount_due=data["totalAmountDue"],
            total_amount_paid=data["totalAmountPaid"],
            total_balance=data["totalBalance"],
            paid_count=data["paidCount"],
            partially_paid_count=data["partiallyPaidCount"],
            unpaid_count=data["unpaidCount"],
        )
