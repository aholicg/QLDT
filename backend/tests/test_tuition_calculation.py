from datetime import date
from decimal import Decimal

import pytest

from app.service.tuition.tuition_calculator import (
    calculate_discount,
    calculate_installments,
    calculate_subject_tuition,
    resolve_tuition_rate,
)
from app.service.tuition.vietnamese_words import number_to_vietnamese_words


def test_number_to_vietnamese_words():
    assert number_to_vietnamese_words(0) == "Không đồng"
    assert number_to_vietnamese_words(12345000) == "Mười hai triệu ba trăm bốn mươi lăm nghìn đồng"
    assert number_to_vietnamese_words(15000000) == "Mười lăm triệu đồng"
    assert number_to_vietnamese_words(1005000) == "Một triệu không trăm lẻ năm nghìn đồng"
    assert number_to_vietnamese_words(21000) == "Hai mươi mốt nghìn đồng"
    assert number_to_vietnamese_words(100000000) == "Một trăm triệu đồng"


def test_calculate_subject_tuition_decimal_and_rounding():
    # Môn 3 TCHP đơn giá 450.000
    assert calculate_subject_tuition(3, 450000) == 1350000
    # Môn 1.5 TCHP đơn giá 450.000
    assert calculate_subject_tuition(Decimal("1.5"), 450000) == 675000
    # Môn 3.6 TCHP đơn giá 478.125 -> 1721250
    assert calculate_subject_tuition(Decimal("3.6"), 478125) == 1721250
    # Kiểm tra làm tròn xuống đồng
    assert calculate_subject_tuition(Decimal("1.33"), 10000) == 13300


def test_calculate_discount_order_and_bounds():
    total = 10000000  # 10 triệu
    # Giảm 30% và cố định 1 triệu -> Giảm 3tr + 1tr = 4tr; Cần nộp 6tr
    discount, due = calculate_discount(
        total, discount_percent=Decimal("30.00"), fixed_amount=1000000
    )
    assert discount == 4000000
    assert due == 6000000

    with pytest.raises(ValueError, match="vượt quá"):
        calculate_discount(total, discount_percent=Decimal("80.00"), fixed_amount=5000000)

    # Không miễn giảm
    discount, due = calculate_discount(total)
    assert discount == 0
    assert due == 10000000


def test_calculate_installments_rounding_remainder():
    amount_due = 10000000
    specs = [
        {"installmentOrder": 1, "percentage": Decimal("50.00")},
        {"installmentOrder": 2, "percentage": Decimal("30.00")},
        {"installmentOrder": 3, "percentage": Decimal("20.00")},
    ]
    results = calculate_installments(amount_due, specs)
    assert len(results) == 3
    assert results[0]["allocatedAmount"] == 5000000
    assert results[1]["allocatedAmount"] == 3000000
    assert results[2]["allocatedAmount"] == 2000000
    assert sum(r["allocatedAmount"] for r in results) == amount_due

    # Trường hợp số lẻ, phần dư dồn vào đợt cuối
    amount_due_odd = 10000001
    specs_odd = [
        {"installmentOrder": 1, "percentage": Decimal("33.33")},
        {"installmentOrder": 2, "percentage": Decimal("33.33")},
        {"installmentOrder": 3, "percentage": Decimal("33.34")},
    ]
    results_odd = calculate_installments(amount_due_odd, specs_odd)
    total_allocated = sum(r["allocatedAmount"] for r in results_odd)
    assert total_allocated == amount_due_odd


def test_installments_reject_mismatch_and_mixed_modes():
    with pytest.raises(ValueError, match="100%"):
        calculate_installments(1000, [{"percentage": Decimal("70")}])
    with pytest.raises(ValueError, match="trộn"):
        calculate_installments(
            1000,
            [{"percentage": Decimal("50")}, {"fixedAmount": 500}],
        )
    with pytest.raises(ValueError, match="không bằng"):
        calculate_installments(1000, [{"fixedAmount": 400}, {"fixedAmount": 500}])


class FakeRate:
    def __init__(self, cohort, major, price):
        self.cohort = cohort
        self.major = major
        self.price = price
        self.effective_from = date.min
        self.effective_to = None


def test_resolve_tuition_rate_priority():
    r_general = FakeRate(None, None, 450000)
    r_cohort = FakeRate("K66", None, 480000)
    r_major = FakeRate(None, "CNTT", 520000)
    r_specific = FakeRate("K66", "CNTT", 550000)
    r_general.effective_from = date(2026, 1, 1)
    r_general.effective_to = date(2026, 12, 31)
    r_specific.effective_from = date(2026, 1, 1)
    r_specific.effective_to = date(2026, 6, 30)
    r_cohort.effective_to = date(2026, 6, 30)
    r_major.effective_to = date(2026, 6, 30)

    rates = [r_general, r_cohort, r_major, r_specific]

    # Khớp cụ thể nhất (K66, CNTT)
    assert resolve_tuition_rate(rates, "K66", "CNTT").price == 550000
    # Khớp theo cohort khi major khác
    assert resolve_tuition_rate(rates, "K66", "CoKhi").price == 480000
    # Khớp theo major khi cohort khác
    assert resolve_tuition_rate(rates, "K67", "CNTT").price == 520000
    # Khớp bản ghi chung khi cả 2 không có bản ghi cụ thể
    assert resolve_tuition_rate(rates, "K67", "Dien").price == 450000
    assert resolve_tuition_rate(rates, "K66", "CNTT", date(2026, 7, 1)).price == 450000
