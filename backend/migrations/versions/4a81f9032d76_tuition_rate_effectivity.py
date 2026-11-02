"""Add effective dates to tuition rates.

Revision ID: 4a81f9032d76
Revises: 79e0a29b3c41
"""

import sqlalchemy as sa
from alembic import op

revision = "4a81f9032d76"
down_revision = "79e0a29b3c41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "TUITION_RATES",
        sa.Column("effective_from", sa.Date(), nullable=True),
    )
    op.add_column(
        "TUITION_RATES",
        sa.Column("effective_to", sa.Date(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE TUITION_RATES SET effective_from = "
            "(SELECT start_date FROM SEMESTERS "
            "WHERE SEMESTERS.semester_id = TUITION_RATES.semester_id)"
        )
    )
    with op.batch_alter_table("TUITION_RATES") as batch_op:
        batch_op.alter_column(
            "effective_from",
            existing_type=sa.Date(),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_TUITION_RATES_effective_range_valid",
            "effective_to IS NULL OR effective_to >= effective_from",
        )
    with op.batch_alter_table("TUITION_INSTALLMENTS") as batch_op:
        batch_op.create_check_constraint(
            "ck_TUITION_INSTALLMENTS_amount_basis_exactly_one",
            "(percentage IS NOT NULL AND fixed_amount IS NULL) OR "
            "(percentage IS NULL AND fixed_amount IS NOT NULL)",
        )
        batch_op.create_check_constraint(
            "ck_TUITION_INSTALLMENTS_percentage_range",
            "percentage IS NULL OR (percentage >= 0 AND percentage <= 100)",
        )
        batch_op.create_check_constraint(
            "ck_TUITION_INSTALLMENTS_fixed_amount_non_negative",
            "fixed_amount IS NULL OR fixed_amount >= 0",
        )
    op.create_index(
        "idx_tuition_rates_effective_lookup",
        "TUITION_RATES",
        ["semester_id", "cohort", "major", "effective_from", "effective_to"],
    )


def downgrade() -> None:
    op.drop_index("idx_tuition_rates_effective_lookup", table_name="TUITION_RATES")
    with op.batch_alter_table("TUITION_INSTALLMENTS") as batch_op:
        batch_op.drop_constraint("ck_TUITION_INSTALLMENTS_fixed_amount_non_negative", type_="check")
        batch_op.drop_constraint("ck_TUITION_INSTALLMENTS_percentage_range", type_="check")
        batch_op.drop_constraint("ck_TUITION_INSTALLMENTS_amount_basis_exactly_one", type_="check")
    with op.batch_alter_table("TUITION_RATES") as batch_op:
        batch_op.drop_constraint("ck_TUITION_RATES_effective_range_valid", type_="check")
        batch_op.drop_column("effective_to")
        batch_op.drop_column("effective_from")
