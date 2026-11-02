from __future__ import annotations

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Query, Response, status

from app.controller.pagination import Pagination
from app.core.database import DbSession
from app.dto.common import ItemList, Page
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
    TuitionRateCreateRequest,
    TuitionRateResponse,
    TuitionRateUpdateRequest,
    TuitionSummaryDto,
)
from app.entity.tuition.tuition_invoice import InvoiceStatus
from app.security.dependencies import AdminUser, CurrentUser, StudentUser
from app.service.tuition.receipt_pdf import render_receipt_pdf
from app.service.tuition.tuition_service import TuitionService

student_router = APIRouter(tags=["tuition"])
admin_router = APIRouter(prefix="/admin", tags=["tuition-admin"])
receipt_router = APIRouter(prefix="/receipts", tags=["receipts"])
router = APIRouter()
router.include_router(student_router)
router.include_router(admin_router)
router.include_router(receipt_router)


@student_router.get("/tuition/me", response_model=TuitionInvoiceDto)
def get_my_tuition(
    user: StudentUser,
    db: DbSession,
    semester_id: Annotated[int | None, Query(alias="semesterId", ge=1)] = None,
):
    return TuitionService(db).get_student_tuition(user, semester_id)


@student_router.post(
    "/tuition/me/payments", response_model=ReceiptDto, status_code=status.HTTP_201_CREATED
)
def make_payment(request: PaymentCreateRequest, user: StudentUser, db: DbSession):
    return TuitionService(db).make_payment(user, request)


@receipt_router.get("/me", response_model=ItemList[ReceiptDto])
def list_my_receipts(
    user: StudentUser,
    db: DbSession,
    semester_id: Annotated[int | None, Query(alias="semesterId", ge=1)] = None,
):
    return ItemList(items=TuitionService(db).list_student_receipts(user, semester_id))


@receipt_router.get("/{receipt_id}/pdf")
def download_receipt_pdf(receipt_id: int, user: CurrentUser, db: DbSession):
    receipt = TuitionService(db).get_receipt(user, receipt_id)
    content = render_receipt_pdf(receipt.model_dump(by_alias=True, mode="json"))
    filename = quote(f"{receipt.receipt_no}.pdf")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@receipt_router.get("/{receipt_id}", response_model=ReceiptDto)
def get_receipt(receipt_id: int, user: CurrentUser, db: DbSession):
    return TuitionService(db).get_receipt(user, receipt_id)


@admin_router.get("/tuition-rates", response_model=ItemList[TuitionRateResponse])
def list_tuition_rates(
    _admin: AdminUser,
    db: DbSession,
    semester_id: Annotated[int | None, Query(alias="semesterId", ge=1)] = None,
):
    return ItemList(items=TuitionService(db).list_rates(semester_id))


@admin_router.post(
    "/tuition-rates",
    response_model=TuitionRateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tuition_rate(request: TuitionRateCreateRequest, _admin: AdminUser, db: DbSession):
    return TuitionService(db).create_rate(request)


@admin_router.put("/tuition-rates/{rate_id}", response_model=TuitionRateResponse)
def update_tuition_rate(
    rate_id: int, request: TuitionRateUpdateRequest, _admin: AdminUser, db: DbSession
):
    return TuitionService(db).update_rate(rate_id, request)


@admin_router.delete("/tuition-rates/{rate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tuition_rate(rate_id: int, _admin: AdminUser, db: DbSession):
    TuitionService(db).delete_rate(rate_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.get("/tuition/discounts", response_model=ItemList[TuitionDiscountResponse])
def list_tuition_discounts(
    _admin: AdminUser,
    db: DbSession,
    semester_id: Annotated[int | None, Query(alias="semesterId", ge=1)] = None,
    student_id: Annotated[int | None, Query(alias="studentId", ge=1)] = None,
):
    return ItemList(items=TuitionService(db).list_discounts(semester_id, student_id))


@admin_router.post(
    "/tuition/discounts",
    response_model=TuitionDiscountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tuition_discount(request: TuitionDiscountCreateRequest, admin: AdminUser, db: DbSession):
    return TuitionService(db).create_discount(request, admin.full_name)


@admin_router.delete("/tuition/discounts/{discount_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tuition_discount(discount_id: int, _admin: AdminUser, db: DbSession):
    TuitionService(db).delete_discount(discount_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.get("/tuition/installments", response_model=ItemList[TuitionInstallmentResponse])
def list_tuition_installments(
    _admin: AdminUser,
    db: DbSession,
    semester_id: Annotated[int, Query(alias="semesterId", ge=1)],
):
    return ItemList(items=TuitionService(db).list_installments(semester_id))


@admin_router.put("/tuition/installments", response_model=ItemList[TuitionInstallmentResponse])
def configure_tuition_installments(
    request: TuitionInstallmentsPutRequest, _admin: AdminUser, db: DbSession
):
    return ItemList(items=TuitionService(db).configure_installments(request))


@admin_router.post("/tuition/invoices/generate", response_model=InvoiceGenerateResult)
def generate_tuition_invoices(request: InvoiceGenerateRequest, _admin: AdminUser, db: DbSession):
    return TuitionService(db).generate_invoices(request)


@admin_router.get("/tuition/invoices", response_model=Page[TuitionInvoiceDto])
def list_tuition_invoices(
    _admin: AdminUser,
    db: DbSession,
    paging: Pagination,
    semester_id: Annotated[int, Query(alias="semesterId", ge=1)],
    invoice_status: Annotated[InvoiceStatus | None, Query(alias="status")] = None,
    student_code: Annotated[str | None, Query(alias="studentCode")] = None,
):
    return TuitionService(db).list_admin_invoices(semester_id, invoice_status, student_code, paging)


@admin_router.get("/tuition/reports/summary", response_model=TuitionSummaryDto)
def tuition_summary(
    _admin: AdminUser,
    db: DbSession,
    semester_id: Annotated[int, Query(alias="semesterId", ge=1)],
):
    return TuitionService(db).get_summary(semester_id)
