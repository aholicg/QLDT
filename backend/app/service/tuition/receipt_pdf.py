from __future__ import annotations

import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings
from app.service.tuition.vietnamese_words import number_to_vietnamese_words

logger = logging.getLogger(__name__)
_REGULAR_FONT = "QLDTReceipt"
_BOLD_FONT = "QLDTReceiptBold"


def _font_path() -> Path:
    if settings.receipt_font_path:
        path = Path(settings.receipt_font_path)
        if path.is_file():
            return path
        raise FileNotFoundError(f"Không tìm thấy font biên lai tại {path}")

    candidates = [
        Path(__file__).resolve().parents[2] / "assets" / "fonts" / "NotoSans-Regular.ttf",
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts" / "arial.ttf",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "Không tìm thấy font Unicode cho biên lai. Đặt RECEIPT_FONT_PATH tới Noto Sans hoặc Roboto."
    )


def _register_fonts() -> None:
    if _REGULAR_FONT in pdfmetrics.getRegisteredFontNames():
        return
    regular = _font_path()
    pdfmetrics.registerFont(TTFont(_REGULAR_FONT, str(regular)))

    configured_bold = settings.receipt_font_path
    bold_candidates = [
        Path(configured_bold) if configured_bold else regular.with_name("NotoSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
        Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts" / "arialbd.ttf",
    ]
    bold = next((path for path in bold_candidates if path.is_file()), regular)
    pdfmetrics.registerFont(TTFont(_BOLD_FONT, str(bold)))


def _money(value: Any) -> str:
    return f"{int(value or 0):,}".replace(",", ".") + " ₫"


def _text(value: Any) -> str:
    return escape(str(value or ""))


def _logo_flowable() -> Any:
    configured = settings.receipt_logo_path
    logo_path = (
        Path(configured)
        if configured
        else (Path(__file__).resolve().parents[2] / "assets" / "logo.png")
    )
    if logo_path.is_file():
        return Image(str(logo_path), width=25 * mm, height=18 * mm, kind="proportional")

    logger.warning("Không tìm thấy logo biên lai tại %s; sử dụng placeholder", logo_path)
    placeholder = Table([["LOGO"]], colWidths=[25 * mm], rowHeights=[18 * mm])
    placeholder.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.7, colors.grey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), _BOLD_FONT),
            ]
        )
    )
    return placeholder


def _qr_flowable(receipt_no: str) -> Drawing:
    qr = QrCodeWidget(receipt_no)
    bounds = qr.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    drawing = Drawing(30 * mm, 30 * mm, transform=[30 * mm / width, 0, 0, 30 * mm / height, 0, 0])
    drawing.add(qr)
    return drawing


def render_receipt_pdf(receipt: dict[str, Any]) -> bytes:
    """Render a receipt exclusively from its immutable snapshot."""
    _register_fonts()
    data = receipt["receiptData"]
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "ReceiptBody",
            parent=styles["BodyText"],
            fontName=_REGULAR_FONT,
            fontSize=9,
            leading=13,
        )
    )
    styles.add(
        ParagraphStyle(
            "ReceiptTitle",
            parent=styles["Title"],
            fontName=_BOLD_FONT,
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#8d1728"),
        )
    )
    styles.add(
        ParagraphStyle(
            "ReceiptRight",
            parent=styles["ReceiptBody"],
            alignment=TA_RIGHT,
        )
    )

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        pageCompression=0,
        title=f"Biên lai {data['receiptNo']}",
        author="Hệ thống quản lý đào tạo",
    )
    story: list[Any] = [
        Table(
            [
                [
                    _logo_flowable(),
                    Paragraph(
                        "<b>ĐẠI HỌC BÁCH KHOA HÀ NỘI</b><br/>BỘ PHẬN THU HỌC PHÍ",
                        styles["ReceiptBody"],
                    ),
                ]
            ],
            colWidths=[35 * mm, 135 * mm],
            style=TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]),
        ),
        Spacer(1, 8 * mm),
        Paragraph("BIÊN LAI THU HỌC PHÍ", styles["ReceiptTitle"]),
        Spacer(1, 4 * mm),
        Paragraph(f"Số biên lai: <b>{_text(data['receiptNo'])}</b>", styles["ReceiptBody"]),
        Paragraph(f"Ngày giờ: {_text(receipt['issuedAt'])}", styles["ReceiptBody"]),
        Paragraph(
            f"Sinh viên: <b>{_text(data['fullName'])}</b> · MSSV: {_text(data['studentCode'])}",
            styles["ReceiptBody"],
        ),
        Paragraph(
            f"Khóa/ngành: {_text(data['cohort'])} / {_text(data['major'])} · "
            f"Học kỳ: {_text(data['semesterCode'])} - {_text(data['semesterName'])}",
            styles["ReceiptBody"],
        ),
        Spacer(1, 3 * mm),
    ]

    rows = [["Mã môn", "Tên môn", "TC", "TCHP", "Đơn giá", "Thành tiền"]]
    for item in data["items"]:
        rows.append(
            [
                _text(item["subjectCode"]),
                Paragraph(_text(item["subjectName"]), styles["ReceiptBody"]),
                str(item["credits"]),
                str(item["tuitionCredits"]),
                _money(item["pricePerCredit"]),
                _money(item["amount"]),
            ]
        )
    course_table = Table(
        rows,
        repeatRows=1,
        colWidths=[20 * mm, 58 * mm, 10 * mm, 13 * mm, 30 * mm, 34 * mm],
    )
    course_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1e4e6")),
                ("FONTNAME", (0, 0), (-1, 0), _BOLD_FONT),
                ("FONTNAME", (0, 1), (-1, -1), _REGULAR_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c9cdd1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend(
        [
            course_table,
            Spacer(1, 4 * mm),
            Paragraph(f"Tổng học phí: {_money(data['totalTuition'])}", styles["ReceiptRight"]),
            Paragraph(f"Miễn giảm: {_money(data['totalDiscount'])}", styles["ReceiptRight"]),
            Paragraph(f"Số phải nộp: {_money(data['amountDue'])}", styles["ReceiptRight"]),
            Paragraph(
                f"Số tiền đợt này: <b>{_money(data['paymentAmount'])}</b>", styles["ReceiptRight"]
            ),
            Paragraph(f"Đã nộp lũy kế: {_money(data['cumulativePaid'])}", styles["ReceiptRight"]),
            Paragraph(f"Còn lại: {_money(data['balanceRemaining'])}", styles["ReceiptRight"]),
            Paragraph(
                f"Bằng chữ: {number_to_vietnamese_words(int(data['paymentAmount']))}",
                styles["ReceiptBody"],
            ),
            Paragraph(f"Phương thức: {_text(data['paymentMethod'])}", styles["ReceiptBody"]),
            Spacer(1, 8 * mm),
            Table(
                [
                    [_qr_flowable(data["receiptNo"]), "Người nộp tiền", "Người thu tiền"],
                    ["", "(Ký, ghi rõ họ tên)", "(Ký, ghi rõ họ tên)"],
                    ["", "", "Nơi đóng dấu"],
                ],
                colWidths=[56 * mm, 56 * mm, 56 * mm],
                rowHeights=[32 * mm, 10 * mm, 14 * mm],
                style=TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), _REGULAR_FONT),
                        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                ),
            ),
        ]
    )
    document.build(story)
    return output.getvalue()
