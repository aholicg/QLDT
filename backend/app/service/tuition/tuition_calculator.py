"""Engine tính toán học phí theo tín chỉ học phí (TCHP) và quy tắc HUST."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any


def calculate_subject_tuition(
    tuition_credits: Decimal | float | int | str,
    price_per_credit: int,
) -> int:
    """Tính học phí môn học = tuition_credits * price_per_credit.

    Làm tròn xuống đến đồng (int). Tuyệt đối không dùng float trong tính toán tiền tệ.
    """
    tc_dec = Decimal(str(tuition_credits))
    rate_dec = Decimal(str(price_per_credit))
    return int(tc_dec * rate_dec)


def calculate_discount(
    total_tuition: int,
    discount_percent: Decimal | float | str = Decimal("0.00"),
    fixed_amount: int = 0,
) -> tuple[int, int]:
    """Tính miễn giảm học phí và số tiền phải nộp.

    Quy tắc:
    - Áp phần trăm trước rồi mới trừ số tiền cố định.
    - Làm tròn xuống đến đồng.
    - Tổng miễn giảm không vượt quá tổng học phí.
    Trả về (total_discount, amount_due).
    """
    if total_tuition <= 0:
        return 0, 0

    pct_dec = Decimal(str(discount_percent))
    total_dec = Decimal(str(total_tuition))

    percent_discount = int(total_dec * pct_dec / Decimal("100"))
    combined = percent_discount + int(fixed_amount)
    if combined > total_tuition:
        raise ValueError("Tổng miễn giảm vượt quá tổng học phí")
    total_discount = max(0, combined)
    amount_due = total_tuition - total_discount
    return total_discount, amount_due


def calculate_installments(
    amount_due: int,
    installment_specs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Phân bổ số tiền phải nộp vào các đợt nộp đã cấu hình.

    Quy tắc:
    - Tổng các đợt đúng bằng số phải nộp amount_due.
    - Phần dư làm tròn được dồn vào đợt cuối cùng.
    """
    if not installment_specs:
        return []

    if amount_due <= 0:
        return [{**spec, "allocatedAmount": 0} for spec in installment_specs]

    modes = {
        "percentage" if spec.get("percentage") is not None else "fixed"
        for spec in installment_specs
    }
    if len(modes) != 1:
        raise ValueError("Không được trộn tỷ lệ phần trăm và số tiền cố định")

    n = len(installment_specs)
    if modes == {"percentage"}:
        total_percentage = sum(
            (Decimal(str(spec["percentage"])) for spec in installment_specs),
            Decimal("0"),
        )
        if total_percentage != Decimal("100"):
            raise ValueError("Tổng tỷ lệ các đợt phải bằng 100%")
    else:
        total_fixed = sum(
            int(spec.get("fixed_amount", spec.get("fixedAmount", 0)) or 0)
            for spec in installment_specs
        )
        if total_fixed != amount_due:
            raise ValueError("Tổng số tiền các đợt không bằng số phải nộp")

    results: list[dict[str, Any]] = []
    sum_allocated = 0

    for i, spec in enumerate(installment_specs):
        if i == n - 1:
            amount = amount_due - sum_allocated
        else:
            pct = spec.get("percentage")
            fixed = spec.get("fixed_amount") or spec.get("fixedAmount")
            if pct is not None:
                amount = int(Decimal(str(amount_due)) * Decimal(str(pct)) / Decimal("100"))
            elif fixed is not None:
                amount = int(fixed)
            else:
                amount = 0
            sum_allocated += amount
        results.append({**spec, "allocatedAmount": max(0, amount)})

    return results


def resolve_tuition_rate(
    rates: list[Any],
    cohort: str | None,
    major: str | None,
    effective_date: date | None = None,
) -> Any | None:
    """Chọn bản ghi đơn giá khớp nhất cho sinh viên theo thứ tự ưu tiên:

    1. Khớp cả cohort và major
    2. Khớp cohort, major là None (áp dụng chung cho khóa)
    3. cohort là None, khớp major (áp dụng chung cho ngành)
    4. Cả cohort và major đều là None (đơn giá chung toàn trường)
    """
    if effective_date is not None:
        rates = [
            rate
            for rate in rates
            if rate.effective_from <= effective_date
            and (rate.effective_to is None or rate.effective_to >= effective_date)
        ]
    if not rates:
        return None

    # Mức 1: Khớp cả cohort và major
    if cohort and major:
        for r in rates:
            if getattr(r, "cohort", None) == cohort and getattr(r, "major", None) == major:
                return r

    # Mức 2: Khớp cohort, major is None
    if cohort:
        for r in rates:
            if getattr(r, "cohort", None) == cohort and getattr(r, "major", None) is None:
                return r

    # Mức 3: cohort is None, khớp major
    if major:
        for r in rates:
            if getattr(r, "cohort", None) is None and getattr(r, "major", None) == major:
                return r

    # Mức 4: Cả 2 đều None
    for r in rates:
        if getattr(r, "cohort", None) is None and getattr(r, "major", None) is None:
            return r

    return None
