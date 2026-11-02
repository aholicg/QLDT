from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import Field, model_validator

from app.dto.common import CamelModel, VNDateTime


class TuitionRateResponse(CamelModel):
    id: int
    semester_id: int
    cohort: str | None = None
    major: str | None = None
    effective_from: date
    effective_to: date | None = None
    price_per_credit: int
    description: str | None = None
    created_at: VNDateTime


class TuitionRateCreateRequest(CamelModel):
    semester_id: int
    cohort: str | None = None
    major: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    price_per_credit: int = Field(..., gt=0)
    description: str | None = None


class TuitionRateUpdateRequest(CamelModel):
    cohort: str | None = None
    major: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    price_per_credit: int = Field(..., gt=0)
    description: str | None = None


class TuitionDiscountResponse(CamelModel):
    id: int
    student_id: int
    student_code: str | None = None
    student_name: str | None = None
    semester_id: int
    discount_percent: float
    fixed_amount: int
    reason: str
    granted_by: str
    created_at: VNDateTime


class TuitionDiscountCreateRequest(CamelModel):
    student_id: int | None = None
    student_code: str | None = None
    semester_id: int
    discount_percent: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    fixed_amount: int = Field(default=0, ge=0)
    reason: str = Field(..., min_length=1)


class TuitionInstallmentResponse(CamelModel):
    id: int
    semester_id: int
    installment_order: int
    name: str
    due_date: date
    percentage: float | None = None
    fixed_amount: int | None = None
    allocated_amount: int | None = None
    status: str | None = None  # PENDING | PAID | OVERDUE


class TuitionInstallmentConfig(CamelModel):
    installment_order: int = Field(..., gt=0)
    name: str = Field(..., min_length=1)
    due_date: date
    percentage: Decimal | None = Field(default=None, ge=0, le=100)
    fixed_amount: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_one_amount_basis(self) -> TuitionInstallmentConfig:
        if (self.percentage is None) == (self.fixed_amount is None):
            raise ValueError("Mỗi đợt phải cấu hình đúng một trong tỷ lệ hoặc số tiền")
        return self


class TuitionInstallmentsPutRequest(CamelModel):
    semester_id: int
    installments: list[TuitionInstallmentConfig]


class TuitionInvoiceItemDto(CamelModel):
    id: int
    subject_id: int
    subject_code: str
    subject_name: str
    credits: int
    tuition_credits: float
    price_per_credit: int
    amount: int


class TuitionPaymentDto(CamelModel):
    id: int
    amount: int
    idempotency_key: str
    payment_method: str
    paid_at: VNDateTime
    receipt_no: str | None = None


class TuitionInvoiceDto(CamelModel):
    id: int
    student_id: int
    student_code: str | None = None
    student_name: str | None = None
    cohort: str | None = None
    major: str | None = None
    semester_id: int
    semester_code: str | None = None
    total_tuition: int
    total_discount: int
    amount_due: int
    amount_paid: int
    balance: int
    status: str
    is_stale: bool
    items: list[TuitionInvoiceItemDto] = Field(default_factory=list)
    discounts: list[TuitionDiscountResponse] = Field(default_factory=list)
    installments: list[TuitionInstallmentResponse] = Field(default_factory=list)
    payments: list[TuitionPaymentDto] = Field(default_factory=list)
    created_at: VNDateTime
    updated_at: VNDateTime


class PaymentCreateRequest(CamelModel):
    installment_id: int | None = None
    amount: int = Field(..., gt=0)
    idempotency_key: str = Field(..., min_length=1, max_length=64)


class ReceiptDto(CamelModel):
    id: int
    receipt_no: str
    payment_id: int
    student_id: int
    student_code: str | None = None
    student_name: str | None = None
    invoice_id: int
    amount: int
    amount_in_words: str | None = None
    issued_at: VNDateTime
    receipt_data: dict[str, Any]


class InvoiceGenerateRequest(CamelModel):
    semester_id: int
    student_id: int | None = None


class InvoiceGenerateResult(CamelModel):
    total_generated: int
    total_skipped: int
    message: str


class TuitionSummaryDto(CamelModel):
    semester_id: int
    semester_code: str | None = None
    total_invoices: int
    total_amount_due: int
    total_amount_paid: int
    total_balance: int
    paid_count: int
    partially_paid_count: int
    unpaid_count: int
