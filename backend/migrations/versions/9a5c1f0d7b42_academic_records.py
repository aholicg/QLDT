"""Add attendance and section grade records.

Revision ID: 9a5c1f0d7b42
Revises: 68dc54542154
"""

import sqlalchemy as sa
from alembic import op

revision = "9a5c1f0d7b42"
down_revision = "68dc54542154"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ATTENDANCE_RECORDS",
        sa.Column(
            "attendance_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "section_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column(
            "student_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column("class_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PRESENT", "ABSENT", "LATE", "EXCUSED", name="attendance_status"),
            nullable=False,
        ),
        sa.Column(
            "marked_by_user_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["COURSE_SECTIONS.section_id"],
            name=op.f("fk_ATTENDANCE_RECORDS_section_id_COURSE_SECTIONS"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["STUDENTS.student_id"],
            name=op.f("fk_ATTENDANCE_RECORDS_student_id_STUDENTS"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["marked_by_user_id"],
            ["USERS.user_id"],
            name=op.f("fk_ATTENDANCE_RECORDS_marked_by_user_id_USERS"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("attendance_id", name=op.f("pk_ATTENDANCE_RECORDS")),
        sa.UniqueConstraint(
            "section_id",
            "student_id",
            "class_date",
            name="uq_attendance_section_student_date",
        ),
    )
    op.create_index(
        "ix_attendance_section_date",
        "ATTENDANCE_RECORDS",
        ["section_id", "class_date"],
        unique=False,
    )
    op.create_table(
        "SECTION_GRADE_COMPONENTS",
        sa.Column(
            "component_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "section_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("weight_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("max_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "weight_percentage > 0 AND weight_percentage <= 100",
            name=op.f("ck_SECTION_GRADE_COMPONENTS_weight_percentage_range"),
        ),
        sa.CheckConstraint(
            "max_score > 0", name=op.f("ck_SECTION_GRADE_COMPONENTS_max_score_positive")
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["COURSE_SECTIONS.section_id"],
            name=op.f("fk_SECTION_GRADE_COMPONENTS_section_id_COURSE_SECTIONS"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("component_id", name=op.f("pk_SECTION_GRADE_COMPONENTS")),
        sa.UniqueConstraint("section_id", "name", name="uq_grade_components_section_name"),
        sa.UniqueConstraint("section_id", "sort_order", name="uq_grade_components_section_order"),
    )
    op.create_index(
        "ix_grade_components_section",
        "SECTION_GRADE_COMPONENTS",
        ["section_id"],
        unique=False,
    )
    op.create_table(
        "STUDENT_GRADES",
        sa.Column(
            "grade_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "component_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "student_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_by_user_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
        ),
        sa.CheckConstraint("score >= 0", name=op.f("ck_STUDENT_GRADES_score_nonnegative")),
        sa.ForeignKeyConstraint(
            ["component_id"],
            ["SECTION_GRADE_COMPONENTS.component_id"],
            name=op.f("fk_STUDENT_GRADES_component_id_SECTION_GRADE_COMPONENTS"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["STUDENTS.student_id"],
            name=op.f("fk_STUDENT_GRADES_student_id_STUDENTS"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["USERS.user_id"],
            name=op.f("fk_STUDENT_GRADES_updated_by_user_id_USERS"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("grade_id", name=op.f("pk_STUDENT_GRADES")),
        sa.UniqueConstraint(
            "component_id", "student_id", name="uq_student_grades_component_student"
        ),
    )
    op.create_index("ix_student_grades_student", "STUDENT_GRADES", ["student_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_student_grades_student", table_name="STUDENT_GRADES")
    op.drop_table("STUDENT_GRADES")
    op.drop_index("ix_grade_components_section", table_name="SECTION_GRADE_COMPONENTS")
    op.drop_table("SECTION_GRADE_COMPONENTS")
    op.drop_index("ix_attendance_section_date", table_name="ATTENDANCE_RECORDS")
    op.drop_table("ATTENDANCE_RECORDS")
