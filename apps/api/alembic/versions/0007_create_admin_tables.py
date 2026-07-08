"""Create Enterprise Administration tables and permissions.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-01

Adds:
  - system_config      — key/value platform configuration store
  - admin:read  permission  (granted to Administrator + Senior Investigator)
  - admin:write permission  (granted to Administrator only)
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── system_config ─────────────────────────────────────────────────────────
    op.create_table(
        "system_config",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "updated_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    bind = op.get_bind()

    # ── Seed default system_config entries ────────────────────────────────────
    defaults = [
        ("max_evidence_size_mb", "500", "Maximum evidence file size in MB", False),
        ("session_timeout_minutes", "60", "User session inactivity timeout", False),
        ("max_failed_logins", "5", "Lock account after N failed login attempts", False),
        ("lockout_duration_minutes", "30", "Duration of account lockout in minutes", False),
        ("ocr_enabled", "true", "Enable OCR text extraction for evidence", False),
        ("ai_enabled", "false", "Enable AI analysis features", False),
        ("opensearch_enabled", "false", "Enable OpenSearch full-text indexing", False),
        ("retention_days_evidence", "3650", "Evidence retention period in days (0 = forever)", False),
        ("retention_days_audit", "2555", "Audit log retention in days (7 years)", False),
        ("maintenance_mode", "false", "Put platform into maintenance mode", False),
        ("allow_user_registration", "false", "Allow public user self-registration", False),
        ("require_mfa", "false", "Require MFA for all users", False),
        ("max_cases_per_investigator", "50", "Maximum active cases per investigator", False),
        ("ai_rate_limit_per_hour", "100", "Max AI requests per user per hour", False),
        ("storage_warning_pct", "80", "Storage warning threshold percentage", False),
    ]
    for key, val, desc, is_secret in defaults:
        bind.execute(
            sa.text(
                "INSERT INTO system_config (key, value, description, is_secret) "
                "VALUES (:k, :v, :d, :s) ON CONFLICT (key) DO NOTHING"
            ),
            {"k": key, "v": val, "d": desc, "s": is_secret},
        )

    # ── New permissions: admin:read + admin:write ──────────────────────────────
    admin_read_id = str(uuid.uuid4())
    admin_write_id = str(uuid.uuid4())

    bind.execute(
        sa.text(
            "INSERT INTO permissions (id, resource, action, description) VALUES "
            "(:id1, 'admin', 'read',  'View administration dashboards, system health and audit logs'), "
            "(:id2, 'admin', 'write', 'Manage system configuration and administration settings')"
        ),
        {"id1": admin_read_id, "id2": admin_write_id},
    )

    # ── Grant permissions to roles ─────────────────────────────────────────────
    # administrator → admin:read + admin:write
    # senior_investigator → admin:read
    for slug, perm_ids in [
        ("administrator", [admin_read_id, admin_write_id]),
        ("senior_investigator", [admin_read_id]),
    ]:
        row = bind.execute(
            sa.text("SELECT id FROM roles WHERE slug = :s"), {"s": slug}
        ).fetchone()
        if row is None:
            continue
        role_id = str(row[0])
        for perm_id in perm_ids:
            bind.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "VALUES (:r, :p) ON CONFLICT DO NOTHING"
                ),
                {"r": role_id, "p": perm_id},
            )


def downgrade() -> None:
    op.drop_table("system_config")
    op.execute("DELETE FROM permissions WHERE resource = 'admin'")
