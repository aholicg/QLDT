from __future__ import annotations

from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import joinedload, lazyload

from app.entity.auth.student import Student
from app.entity.catalog.course_section import CourseSection
from app.entity.catalog.semester import Semester
from app.entity.catalog.subject import Subject
from app.entity.registration.registration import Registration
from app.entity.tuition.receipt import Receipt
from app.entity.tuition.receipt_sequence import ReceiptSequence
from app.entity.tuition.tuition_discount import TuitionDiscount
from app.entity.tuition.tuition_installment import TuitionInstallment
from app.entity.tuition.tuition_invoice import InvoiceStatus, TuitionInvoice
from app.entity.tuition.tuition_invoice_item import TuitionInvoiceItem
from app.entity.tuition.tuition_payment import TuitionPayment
from app.entity.tuition.tuition_rate import TuitionRate
from app.repository.base import BaseRepository


class TuitionRepository(BaseRepository):
    def lock_semester(self, semester_id: int) -> None:
        self.db.execute(select(Semester.id).where(Semester.id == semester_id).with_for_update())

    def list_students_for_update(self, student_id: int | None = None) -> list[Student]:
        stmt = select(Student).options(lazyload(Student.user)).order_by(Student.id)
        if student_id is not None:
            stmt = stmt.where(Student.id == student_id)
        return list(self.db.scalars(stmt.with_for_update()).all())

    # ==================== TUITION RATES ====================
    def list_rates(self, semester_id: int | None = None) -> list[TuitionRate]:
        stmt = select(TuitionRate).options(joinedload(TuitionRate.semester))
        if semester_id is not None:
            stmt = stmt.where(TuitionRate.semester_id == semester_id)
        stmt = stmt.order_by(TuitionRate.semester_id.desc(), TuitionRate.id.asc())
        return list(self.db.scalars(stmt).all())

    def get_rate_by_id(self, rate_id: int) -> TuitionRate | None:
        stmt = (
            select(TuitionRate)
            .options(joinedload(TuitionRate.semester))
            .where(TuitionRate.id == rate_id)
        )
        return self.db.scalars(stmt).first()

    def add_rate(self, rate: TuitionRate) -> TuitionRate:
        self.db.add(rate)
        self.db.flush()
        return rate

    def delete_rate(self, rate: TuitionRate) -> None:
        self.db.delete(rate)
        self.db.flush()

    # ==================== TUITION DISCOUNTS ====================
    def list_discounts(
        self, semester_id: int | None = None, student_id: int | None = None
    ) -> list[TuitionDiscount]:
        stmt = select(TuitionDiscount).options(
            joinedload(TuitionDiscount.student).joinedload(Student.user),
            joinedload(TuitionDiscount.semester),
        )
        if semester_id is not None:
            stmt = stmt.where(TuitionDiscount.semester_id == semester_id)
        if student_id is not None:
            stmt = stmt.where(TuitionDiscount.student_id == student_id)
        stmt = stmt.order_by(TuitionDiscount.id.desc())
        return list(self.db.scalars(stmt).all())

    def list_discounts_by_students(
        self, semester_id: int, student_ids: list[int]
    ) -> dict[int, list[TuitionDiscount]]:
        if not student_ids:
            return {}
        stmt = (
            select(TuitionDiscount)
            .where(
                TuitionDiscount.semester_id == semester_id,
                TuitionDiscount.student_id.in_(student_ids),
            )
            .order_by(TuitionDiscount.id)
        )
        result: dict[int, list[TuitionDiscount]] = {}
        for discount in self.db.scalars(stmt):
            result.setdefault(discount.student_id, []).append(discount)
        return result

    def get_discount_by_id(self, discount_id: int) -> TuitionDiscount | None:
        stmt = (
            select(TuitionDiscount)
            .options(
                joinedload(TuitionDiscount.student).joinedload(Student.user),
                joinedload(TuitionDiscount.semester),
            )
            .where(TuitionDiscount.id == discount_id)
        )
        return self.db.scalars(stmt).first()

    def add_discount(self, discount: TuitionDiscount) -> TuitionDiscount:
        self.db.add(discount)
        self.db.flush()
        return discount

    def delete_discount(self, discount: TuitionDiscount) -> None:
        self.db.delete(discount)
        self.db.flush()

    # ==================== TUITION INSTALLMENTS ====================
    def list_installments(self, semester_id: int) -> list[TuitionInstallment]:
        stmt = (
            select(TuitionInstallment)
            .options(joinedload(TuitionInstallment.semester))
            .where(TuitionInstallment.semester_id == semester_id)
            .order_by(TuitionInstallment.installment_order.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_installment_by_id(self, installment_id: int) -> TuitionInstallment | None:
        stmt = (
            select(TuitionInstallment)
            .options(joinedload(TuitionInstallment.semester))
            .where(TuitionInstallment.id == installment_id)
        )
        return self.db.scalars(stmt).first()

    def replace_installments(
        self, semester_id: int, installments: list[TuitionInstallment]
    ) -> list[TuitionInstallment]:
        self.db.execute(
            delete(TuitionInstallment).where(TuitionInstallment.semester_id == semester_id)
        )
        for inst in installments:
            self.db.add(inst)
        self.db.flush()
        return installments

    def has_payments_for_semester(self, semester_id: int) -> bool:
        stmt = (
            select(TuitionPayment.id)
            .join(TuitionInvoice, TuitionPayment.invoice_id == TuitionInvoice.id)
            .where(TuitionInvoice.semester_id == semester_id)
            .limit(1)
        )
        return self.db.scalar(stmt) is not None

    def mark_invoices_stale(self, semester_id: int, student_id: int | None = None) -> None:
        stmt = select(TuitionInvoice).where(TuitionInvoice.semester_id == semester_id)
        if student_id is not None:
            stmt = stmt.where(TuitionInvoice.student_id == student_id)
        for invoice in self.db.scalars(stmt):
            invoice.is_stale = True

    # ==================== TUITION INVOICES ====================
    def get_invoice(self, student_id: int, semester_id: int) -> TuitionInvoice | None:
        stmt = (
            select(TuitionInvoice)
            .options(
                joinedload(TuitionInvoice.student).joinedload(Student.user),
                joinedload(TuitionInvoice.semester),
                joinedload(TuitionInvoice.items).joinedload(TuitionInvoiceItem.subject),
                joinedload(TuitionInvoice.payments).joinedload(TuitionPayment.receipt),
            )
            .where(
                TuitionInvoice.student_id == student_id,
                TuitionInvoice.semester_id == semester_id,
            )
        )
        return self.db.scalars(stmt).unique().first()

    def get_invoice_by_id(self, invoice_id: int) -> TuitionInvoice | None:
        stmt = (
            select(TuitionInvoice)
            .options(
                joinedload(TuitionInvoice.student).joinedload(Student.user),
                joinedload(TuitionInvoice.semester),
                joinedload(TuitionInvoice.items).joinedload(TuitionInvoiceItem.subject),
                joinedload(TuitionInvoice.payments).joinedload(TuitionPayment.receipt),
            )
            .where(TuitionInvoice.id == invoice_id)
        )
        return self.db.scalars(stmt).unique().first()

    def get_invoice_by_id_for_update(self, invoice_id: int) -> TuitionInvoice | None:
        stmt = select(TuitionInvoice).where(TuitionInvoice.id == invoice_id).with_for_update()
        return self.db.scalars(stmt).first()

    def get_invoice_by_student_semester_for_update(
        self, student_id: int, semester_id: int
    ) -> TuitionInvoice | None:
        stmt = (
            select(TuitionInvoice)
            .where(
                TuitionInvoice.student_id == student_id,
                TuitionInvoice.semester_id == semester_id,
            )
            .with_for_update()
        )
        return self.db.scalars(stmt).first()

    def list_invoices_for_students_for_update(
        self, semester_id: int, student_ids: list[int]
    ) -> list[TuitionInvoice]:
        if not student_ids:
            return []
        stmt = (
            select(TuitionInvoice)
            .where(
                TuitionInvoice.semester_id == semester_id,
                TuitionInvoice.student_id.in_(student_ids),
            )
            .order_by(TuitionInvoice.student_id)
            .with_for_update()
        )
        return list(self.db.scalars(stmt).all())

    def list_invoices(
        self,
        semester_id: int,
        status: InvoiceStatus | None,
        student_code: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[TuitionInvoice], int]:
        base_stmt = (
            select(TuitionInvoice)
            .join(Student, TuitionInvoice.student_id == Student.id)
            .where(TuitionInvoice.semester_id == semester_id)
        )
        count_stmt = (
            select(func.count(TuitionInvoice.id))
            .join(Student, TuitionInvoice.student_id == Student.id)
            .where(TuitionInvoice.semester_id == semester_id)
        )

        if status is not None:
            base_stmt = base_stmt.where(TuitionInvoice.status == status)
            count_stmt = count_stmt.where(TuitionInvoice.status == status)

        if student_code:
            kw = f"%{student_code.strip()}%"
            base_stmt = base_stmt.where(Student.student_code.ilike(kw))
            count_stmt = count_stmt.where(Student.student_code.ilike(kw))

        total = self.db.scalar(count_stmt) or 0
        items_stmt = (
            base_stmt.options(
                joinedload(TuitionInvoice.student).joinedload(Student.user),
                joinedload(TuitionInvoice.semester),
                joinedload(TuitionInvoice.items),
                joinedload(TuitionInvoice.payments),
            )
            .order_by(Student.student_code.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(items_stmt).unique().all()), total

    def get_summary(self, semester_id: int) -> dict[str, int]:
        totals = self.db.execute(
            select(
                func.count(TuitionInvoice.id),
                func.coalesce(func.sum(TuitionInvoice.amount_due), 0),
                func.coalesce(func.sum(TuitionInvoice.amount_paid), 0),
                func.coalesce(
                    func.sum(case((TuitionInvoice.status == InvoiceStatus.PAID, 1), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(
                        case((TuitionInvoice.status == InvoiceStatus.PARTIALLY_PAID, 1), else_=0)
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(case((TuitionInvoice.status == InvoiceStatus.UNPAID, 1), else_=0)), 0
                ),
            ).where(TuitionInvoice.semester_id == semester_id)
        ).one()
        total_invoices, total_due, total_paid, paid_cnt, part_cnt, unpaid_cnt = totals

        return {
            "totalInvoices": total_invoices,
            "totalAmountDue": total_due,
            "totalAmountPaid": total_paid,
            "totalBalance": max(0, total_due - total_paid),
            "paidCount": paid_cnt,
            "partiallyPaidCount": part_cnt,
            "unpaidCount": unpaid_cnt,
        }

    def add_invoice(self, invoice: TuitionInvoice) -> TuitionInvoice:
        self.db.add(invoice)
        self.db.flush()
        return invoice

    def delete_invoice_items(self, invoice_id: int) -> None:
        self.db.execute(
            delete(TuitionInvoiceItem).where(TuitionInvoiceItem.invoice_id == invoice_id)
        )
        self.db.flush()

    def delete_invoice_items_for_invoices(self, invoice_ids: list[int]) -> None:
        if invoice_ids:
            self.db.execute(
                delete(TuitionInvoiceItem).where(TuitionInvoiceItem.invoice_id.in_(invoice_ids))
            )

    # ==================== TUITION PAYMENTS ====================
    def get_payment_by_key(self, student_id: int, idempotency_key: str) -> TuitionPayment | None:
        stmt = (
            select(TuitionPayment)
            .options(joinedload(TuitionPayment.receipt))
            .where(
                TuitionPayment.student_id == student_id,
                TuitionPayment.idempotency_key == idempotency_key,
            )
        )
        return self.db.scalars(stmt).first()

    def paid_amount_for_installment(self, invoice_id: int, installment_id: int) -> int:
        return int(
            self.db.scalar(
                select(func.coalesce(func.sum(TuitionPayment.amount), 0)).where(
                    TuitionPayment.invoice_id == invoice_id,
                    TuitionPayment.installment_id == installment_id,
                )
            )
            or 0
        )

    def add_payment(self, payment: TuitionPayment) -> TuitionPayment:
        self.db.add(payment)
        self.db.flush()
        return payment

    # ==================== RECEIPTS & SEQUENCES ====================
    def get_receipt_by_id(self, receipt_id: int) -> Receipt | None:
        stmt = (
            select(Receipt)
            .options(
                joinedload(Receipt.student).joinedload(Student.user),
                joinedload(Receipt.invoice).joinedload(TuitionInvoice.semester),
            )
            .where(Receipt.id == receipt_id)
        )
        return self.db.scalars(stmt).first()

    def list_receipts_by_student(
        self, student_id: int, semester_id: int | None = None
    ) -> list[Receipt]:
        stmt = (
            select(Receipt)
            .join(TuitionInvoice, Receipt.invoice_id == TuitionInvoice.id)
            .options(
                joinedload(Receipt.student).joinedload(Student.user),
                joinedload(Receipt.invoice).joinedload(TuitionInvoice.semester),
            )
            .where(Receipt.student_id == student_id)
        )
        if semester_id is not None:
            stmt = stmt.where(TuitionInvoice.semester_id == semester_id)
        stmt = stmt.order_by(Receipt.id.desc())
        return list(self.db.scalars(stmt).all())

    def add_receipt(self, receipt: Receipt) -> Receipt:
        self.db.add(receipt)
        self.db.flush()
        return receipt

    def next_receipt_number(self, semester_id: int, semester_code: str) -> str:
        """Sinh số biên lai tuần tự có khóa dòng chống race condition (BL-<kỳ>-<6 số>)."""
        self.db.execute(select(Semester.id).where(Semester.id == semester_id).with_for_update())
        seq = self.db.scalars(
            select(ReceiptSequence)
            .where(ReceiptSequence.semester_id == semester_id)
            .with_for_update()
        ).first()

        if seq is None:
            seq = ReceiptSequence(semester_id=semester_id, current_number=1)
            self.db.add(seq)
            self.db.flush()
            next_num = 1
        else:
            seq.current_number += 1
            self.db.flush()
            next_num = seq.current_number

        return f"BL-{semester_code}-{next_num:06d}"

    # ==================== BATCH HELPERS ====================
    def get_registered_students_and_subjects(
        self, semester_id: int, student_id: int | None = None
    ) -> dict[int, list[Subject]]:
        """Lấy danh sách môn học đã đăng ký theo từng sinh viên trong 1 query tránh N+1."""
        stmt = (
            select(Registration.student_id, Subject)
            .join(CourseSection, Registration.section_id == CourseSection.id)
            .join(Subject, CourseSection.subject_id == Subject.id)
            .where(CourseSection.semester_id == semester_id)
        )
        if student_id is not None:
            stmt = stmt.where(Registration.student_id == student_id)

        rows = self.db.execute(stmt).all()
        result: dict[int, list[Subject]] = {}
        for sid, subj in rows:
            result.setdefault(sid, []).append(subj)
        return result
