"""Chuyển đổi số tiền thành chữ tiếng Việt chuẩn cho biên lai học phí."""

from __future__ import annotations

UNITS = ["", " nghìn", " triệu", " tỷ", " nghìn tỷ", " triệu tỷ"]
DIGITS = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _read_three_digits(number: int, is_highest: bool) -> str:
    hundreds = number // 100
    tens = (number % 100) // 10
    units = number % 10

    if hundreds == 0 and tens == 0 and units == 0:
        return ""

    parts: list[str] = []

    if hundreds > 0 or not is_highest:
        parts.append(f"{DIGITS[hundreds]} trăm")

    if tens > 1:
        parts.append(f"{DIGITS[tens]} mươi")
        if units == 1:
            parts.append("mốt")
        elif units == 4:
            parts.append("tư")
        elif units == 5:
            parts.append("lăm")
        elif units > 0:
            parts.append(DIGITS[units])
    elif tens == 1:
        parts.append("mười")
        if units == 5:
            parts.append("lăm")
        elif units > 0:
            parts.append(DIGITS[units])
    else:  # tens == 0
        if (hundreds > 0 or not is_highest) and units > 0:
            parts.append(f"lẻ {DIGITS[units]}")
        elif units > 0:
            parts.append(DIGITS[units])

    return " ".join(parts)


def number_to_vietnamese_words(amount: int) -> str:
    """Chuyển số tiền nguyên VND thành chuỗi đọc tiếng Việt có đuôi 'đồng'."""
    if amount == 0:
        return "Không đồng"
    if amount < 0:
        return f"Âm {number_to_vietnamese_words(-amount).lower()}"

    groups: list[int] = []
    temp = amount
    while temp > 0:
        groups.append(temp % 1000)
        temp //= 1000

    parts: list[str] = []
    for i in range(len(groups) - 1, -1, -1):
        grp = groups[i]
        if grp == 0:
            continue
        is_highest = i == len(groups) - 1
        reading = _read_three_digits(grp, is_highest=is_highest)
        unit = UNITS[i] if i < len(UNITS) else ""
        parts.append(f"{reading}{unit}")

    result = " ".join(parts).strip() + " đồng"
    result = " ".join(result.split())
    return result[0].upper() + result[1:]
