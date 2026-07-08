"""Add performance indexes for frequent query patterns.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-01

Adds targeted indexes for columns that appear in WHERE clauses on
high-traffic queries but had no dedicated index.

  * case_assignments.user_id  — used in the private-case visibility subquery
                                on every cases.search() call
  * cases.deleted_at          — every CaseRepository query filters on this
  * users.deleted_at          — every UserRepository query filters on this
  * case_activities.created_at — used for ordering activity feeds
"""

from __future__ import annotations

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # case_assignments.user_id: composite PK is (case_id, user_id) so
    # lookups by user_id alone (visibility subquery) require a separate index.
    op.create_index(
        "ix_case_assignments_user_id",
        "case_assignments",
        ["user_id"],
    )

    # Soft-delete columns: nearly every query filters WHERE deleted_at IS NULL.
    # Partial indexes on NULL would be ideal but require non-transactional DDL;
    # a plain btree index is safe here and still helps the planner.
    op.create_index("ix_cases_deleted_at", "cases", ["deleted_at"])
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])

    # Activity feed ordering
    op.create_index(
        "ix_case_activities_created_at",
        "case_activities",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_case_activities_created_at", table_name="case_activities")
    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_index("ix_cases_deleted_at", table_name="cases")
    op.drop_index("ix_case_assignments_user_id", table_name="case_assignments")
