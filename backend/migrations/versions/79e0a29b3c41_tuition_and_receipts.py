"""tuition and receipts schema

Revision ID: 79e0a29b3c41
Revises: 68dc54542154
Create Date: 2026-10-31 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "79e0a29b3c41"
down_revision = "68dc54542154"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Thêm cột tuition_credits vào bảng SUBJECTS
    op.add_column(
        "SUBJECTS", sa.Column("tuition_credits", sa.Numeric(precision=4, scale=1), nullable=True)
    )

    # 2. Tạo bảng TUITION_RATES
    op.create_table(
        "TUITION_RATES",
        sa.Column(
            "rate_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "semester_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column("cohort", sa.String(length=10), nullable=True),
        sa.Column("major", sa.String(length=100), nullable=True),
        sa.Column(
            "price_per_credit", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("price_per_credit > 0", name=op.f("ck_TUITION_RATES_price_positive")),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["SEMESTERS.semester_id"],
            name=op.f("fk_TUITION_RATES_semester_id_SEMESTERS"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("rate_id", name=op.f("pk_TUITION_RATES")),
    )
    op.create_index("idx_tuition_rates_lookup", "TUITION_RATES", ["semester_id", "cohort", "major"])

    # 3. Tạo bảng TUITION_DISCOUNTS
    op.create_table(
        "TUITION_DISCOUNTS",
        sa.Column(
            "discount_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "student_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column(
            "semester_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column(
            "discount_percent",
            sa.Numeric(precision=5, scale=2),
            server_default="0.00",
            nullable=False,
        ),
        sa.Column(
            "fixed_amount",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            server_default="0",
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("granted_by", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "discount_percent >= 0 AND discount_percent <= 100",
            name=op.f("ck_TUITION_DISCOUNTS_discount_percent_range"),
        ),
        sa.CheckConstraint(
            "fixed_amount >= 0", name=op.f("ck_TUITION_DISCOUNTS_fixed_amount_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["STUDENTS.student_id"],
            name=op.f("fk_TUITION_DISCOUNTS_student_id_STUDENTS"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["SEMESTERS.semester_id"],
            name=op.f("fk_TUITION_DISCOUNTS_semester_id_SEMESTERS"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("discount_id", name=op.f("pk_TUITION_DISCOUNTS")),
    )
    op.create_index(
        "idx_tuition_discounts_student_semester", "TUITION_DISCOUNTS", ["student_id", "semester_id"]
    )

    # 4. Tạo bảng TUITION_INSTALLMENTS
    op.create_table(
        "TUITION_INSTALLMENTS",
        sa.Column(
            "installment_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "semester_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column("installment_order", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("percentage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column(
            "fixed_amount", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True
        ),
        sa.CheckConstraint(
            "installment_order > 0", name=op.f("ck_TUITION_INSTALLMENTS_installment_order_positive")
        ),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["SEMESTERS.semester_id"],
            name=op.f("fk_TUITION_INSTALLMENTS_semester_id_SEMESTERS"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("installment_id", name=op.f("pk_TUITION_INSTALLMENTS")),
        sa.UniqueConstraint(
            "semester_id", "installment_order", name=op.f("uq_installment_semester_order")
        ),
    )

    # 5. Tạo bảng TUITION_INVOICES
    invoice_status_enum = sa.Enum(
        "UNPAID", "PARTIALLY_PAID", "PAID", "CANCELLED", name="invoice_status"
    )
    op.create_table(
        "TUITION_INVOICES",
        sa.Column(
            "invoice_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "student_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column(
            "semester_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column(
            "total_tuition",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "total_discount",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "amount_due",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "amount_paid",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            server_default="0",
            nullable=False,
        ),
        sa.Column("status", invoice_status_enum, server_default="UNPAID", nullable=False),
        sa.Column("is_stale", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "total_tuition >= 0", name=op.f("ck_TUITION_INVOICES_total_tuition_non_negative")
        ),
        sa.CheckConstraint(
            "total_discount >= 0", name=op.f("ck_TUITION_INVOICES_total_discount_non_negative")
        ),
        sa.CheckConstraint(
            "amount_due >= 0", name=op.f("ck_TUITION_INVOICES_amount_due_non_negative")
        ),
        sa.CheckConstraint(
            "amount_paid >= 0", name=op.f("ck_TUITION_INVOICES_amount_paid_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["STUDENTS.student_id"],
            name=op.f("fk_TUITION_INVOICES_student_id_STUDENTS"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["SEMESTERS.semester_id"],
            name=op.f("fk_TUITION_INVOICES_semester_id_SEMESTERS"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("invoice_id", name=op.f("pk_TUITION_INVOICES")),
        sa.UniqueConstraint("student_id", "semester_id", name=op.f("uq_invoice_student_semester")),
    )
    op.create_index(
        "idx_tuition_invoices_student_semester", "TUITION_INVOICES", ["student_id", "semester_id"]
    )

    # 6. Tạo bảng TUITION_INVOICE_ITEMS
    op.create_table(
        "TUITION_INVOICE_ITEMS",
        sa.Column(
            "item_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "invoice_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column(
            "subject_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column("subject_code", sa.String(length=20), nullable=False),
        sa.Column("subject_name", sa.String(length=150), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("tuition_credits", sa.Numeric(precision=4, scale=1), nullable=False),
        sa.Column(
            "price_per_credit", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column("amount", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.CheckConstraint(
            "credits > 0", name=op.f("ck_TUITION_INVOICE_ITEMS_item_credits_positive")
        ),
        sa.CheckConstraint(
            "tuition_credits > 0",
            name=op.f("ck_TUITION_INVOICE_ITEMS_item_tuition_credits_positive"),
        ),
        sa.CheckConstraint(
            "price_per_credit > 0", name=op.f("ck_TUITION_INVOICE_ITEMS_item_price_positive")
        ),
        sa.CheckConstraint(
            "amount >= 0", name=op.f("ck_TUITION_INVOICE_ITEMS_item_amount_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["TUITION_INVOICES.invoice_id"],
            name=op.f("fk_TUITION_INVOICE_ITEMS_invoice_id_TUITION_INVOICES"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["SUBJECTS.subject_id"],
            name=op.f("fk_TUITION_INVOICE_ITEMS_subject_id_SUBJECTS"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("item_id", name=op.f("pk_TUITION_INVOICE_ITEMS")),
    )
    op.create_index("idx_invoice_items_invoice_id", "TUITION_INVOICE_ITEMS", ["invoice_id"])

    # 7. Tạo bảng TUITION_PAYMENTS
    op.create_table(
        "TUITION_PAYMENTS",
        sa.Column(
            "payment_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "invoice_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column(
            "student_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column(
            "installment_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True
        ),
        sa.Column("amount", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column(
            "payment_method", sa.String(length=50), server_default="SIMULATED", nullable=False
        ),
        sa.Column("paid_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name=op.f("ck_TUITION_PAYMENTS_payment_amount_positive")),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["TUITION_INVOICES.invoice_id"],
            name=op.f("fk_TUITION_PAYMENTS_invoice_id_TUITION_INVOICES"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["STUDENTS.student_id"],
            name=op.f("fk_TUITION_PAYMENTS_student_id_STUDENTS"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["installment_id"],
            ["TUITION_INSTALLMENTS.installment_id"],
            name=op.f("fk_TUITION_PAYMENTS_installment_id_TUITION_INSTALLMENTS"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("payment_id", name=op.f("pk_TUITION_PAYMENTS")),
        sa.UniqueConstraint("student_id", "idempotency_key", name=op.f("uq_payment_student_key")),
    )
    op.create_index("idx_tuition_payments_invoice", "TUITION_PAYMENTS", ["invoice_id"])

    # 8. Tạo bảng RECEIPTS
    op.create_table(
        "RECEIPTS",
        sa.Column(
            "receipt_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("receipt_no", sa.String(length=50), nullable=False),
        sa.Column(
            "payment_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column(
            "student_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column(
            "invoice_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column("amount", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("issued_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("receipt_data", sa.JSON(), nullable=False),
        sa.CheckConstraint("amount > 0", name=op.f("ck_RECEIPTS_receipt_amount_positive")),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["TUITION_PAYMENTS.payment_id"],
            name=op.f("fk_RECEIPTS_payment_id_TUITION_PAYMENTS"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["STUDENTS.student_id"],
            name=op.f("fk_RECEIPTS_student_id_STUDENTS"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["TUITION_INVOICES.invoice_id"],
            name=op.f("fk_RECEIPTS_invoice_id_TUITION_INVOICES"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("receipt_id", name=op.f("pk_RECEIPTS")),
        sa.UniqueConstraint("receipt_no", name=op.f("uq_receipt_no")),
        sa.UniqueConstraint("payment_id", name=op.f("uq_receipt_payment")),
    )

    # 9. Tạo bảng RECEIPT_SEQUENCES
    op.create_table(
        "RECEIPT_SEQUENCES",
        sa.Column(
            "semester_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column("current_number", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["semester_id"],
            ["SEMESTERS.semester_id"],
            name=op.f("fk_RECEIPT_SEQUENCES_semester_id_SEMESTERS"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("semester_id", name=op.f("pk_RECEIPT_SEQUENCES")),
    )


def downgrade() -> None:
    op.drop_table("RECEIPT_SEQUENCES")
    op.drop_table("RECEIPTS")
    op.drop_table("TUITION_PAYMENTS")
    op.drop_table("TUITION_INVOICE_ITEMS")
    op.drop_table("TUITION_INVOICES")
    op.drop_table("TUITION_INSTALLMENTS")
    op.drop_table("TUITION_DISCOUNTS")
    op.drop_table("TUITION_RATES")
    op.drop_column("SUBJECTS", "tuition_credits")
