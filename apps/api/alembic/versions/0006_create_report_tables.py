"""Create Investigation Report Intelligence Engine tables + permissions.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-01

Adds:
  - investigation_reports  — report configs + generated content
  - report_exports         — per-format export records
  - report:write / report:publish permissions granted to existing roles
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── investigation_reports ──────────────────────────────────────────────────
    op.create_table(
        "investigation_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("template", sa.String(50), nullable=False, server_default="professional"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column(
            "parent_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigation_reports.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "sections_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "report_filters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "sections_content",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("generation_error", sa.Text, nullable=True),
        sa.Column(
            "generated_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "approved_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_investigation_reports_case_id", "investigation_reports", ["case_id"])
    op.create_index("ix_investigation_reports_status", "investigation_reports", ["status"])
    op.create_index("ix_investigation_reports_report_type", "investigation_reports", ["report_type"])
    op.create_index("ix_investigation_reports_created_at", "investigation_reports", ["created_at"])
    op.create_index("ix_investigation_reports_parent_report_id", "investigation_reports", ["parent_report_id"])

    # ── report_exports ─────────────────────────────────────────────────────────
    op.create_table(
        "report_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("investigation_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column(
            "generated_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_report_exports_report_id", "report_exports", ["report_id"])

    # ── Permissions ────────────────────────────────────────────────────────────
    conn = op.get_bind()

    # Insert permissions
    write_id = str(uuid.uuid4())
    publish_id = str(uuid.uuid4())
    conn.execute(
        sa.text(
            "INSERT INTO permissions (id, resource, action, description) VALUES "
            "(:w_id, 'report', 'write', 'Create and generate investigation reports'),"
            "(:p_id, 'report', 'publish', 'Publish and approve investigation reports')"
            " ON CONFLICT (resource, action) DO NOTHING"
        ),
        {"w_id": write_id, "p_id": publish_id},
    )

    # Grant to all existing roles that have evidence:read (investigators can generate reports)
    conn.execute(
        sa.text("""
            INSERT INTO role_permissions (role_id, permission_id, granted_at)
            SELECT r.id, p.id, NOW()
            FROM roles r
            CROSS JOIN permissions p
            WHERE p.resource = 'report'
              AND p.action IN ('write', 'publish')
              AND r.id IN (
                  SELECT DISTINCT rp.role_id
                  FROM role_permissions rp
                  JOIN permissions pe ON pe.id = rp.permission_id
                  WHERE pe.resource = 'evidence' AND pe.action = 'read'
              )
            ON CONFLICT DO NOTHING
        """)
    )


def downgrade() -> None:
    op.drop_index("ix_report_exports_report_id", table_name="report_exports")
    op.drop_table("report_exports")
    op.drop_index("ix_investigation_reports_parent_report_id", table_name="investigation_reports")
    op.drop_index("ix_investigation_reports_created_at", table_name="investigation_reports")
    op.drop_index("ix_investigation_reports_report_type", table_name="investigation_reports")
    op.drop_index("ix_investigation_reports_status", table_name="investigation_reports")
    op.drop_index("ix_investigation_reports_case_id", table_name="investigation_reports")
    op.drop_table("investigation_reports")
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM permissions WHERE resource = 'report' AND action IN ('write', 'publish')"
        )
    )
