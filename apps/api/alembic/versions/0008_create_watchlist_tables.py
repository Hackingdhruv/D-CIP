"""Create Watchlist & Alert tables and permissions.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-01

Adds:
  - watchlists           — named lists of IOCs / keywords to monitor
  - watchlist_entries    — individual values within a watchlist
  - watchlist_alerts     — generated alerts when evidence matches a watchlist
  - alert_notifications  — per-user server-backed notification feed
  - watchlist:read/write permissions (all roles with case access)
  - alert:read/write permissions
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── watchlists ────────────────────────────────────────────────────────────
    op.create_table(
        "watchlists",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("watchlist_type", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
            nullable=False,
        ),
    )
    op.create_index("ix_watchlists_watchlist_type", "watchlists", ["watchlist_type"])
    op.create_index("ix_watchlists_case_id", "watchlists", ["case_id"])

    # ── watchlist_entries ─────────────────────────────────────────────────────
    op.create_table(
        "watchlist_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "watchlist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("watchlists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("normalized_value", sa.Text(), nullable=False),
        sa.Column("is_regex", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
            nullable=False,
        ),
    )
    op.create_index(
        "ix_watchlist_entries_watchlist_id", "watchlist_entries", ["watchlist_id"]
    )
    op.create_index(
        "ix_watchlist_entries_normalized_value",
        "watchlist_entries",
        ["normalized_value"],
    )

    # ── watchlist_alerts ──────────────────────────────────────────────────────
    op.create_table(
        "watchlist_alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "watchlist_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("watchlists.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "watchlist_entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("watchlist_entries.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidence.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("matched_value", sa.Text(), nullable=True),
        sa.Column("matched_entity_type", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column(
            "is_cross_case", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "cross_case_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "alert_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "acknowledged_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resolved_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
            nullable=False,
        ),
    )
    op.create_index("ix_watchlist_alerts_case_id", "watchlist_alerts", ["case_id"])
    op.create_index(
        "ix_watchlist_alerts_created_at", "watchlist_alerts", ["created_at"]
    )
    op.create_index("ix_watchlist_alerts_status", "watchlist_alerts", ["status"])
    op.create_index(
        "ix_watchlist_alerts_alert_type", "watchlist_alerts", ["alert_type"]
    )
    op.create_index(
        "ix_watchlist_alerts_severity", "watchlist_alerts", ["severity"]
    )
    op.create_index(
        "ix_watchlist_alerts_evidence_id", "watchlist_alerts", ["evidence_id"]
    )
    op.create_index(
        "ix_watchlist_alerts_watchlist_id", "watchlist_alerts", ["watchlist_id"]
    )

    # ── alert_notifications ───────────────────────────────────────────────────
    op.create_table(
        "alert_notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "alert_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("watchlist_alerts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("level", sa.String(20), nullable=False, server_default="info"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_alert_notifications_user_id", "alert_notifications", ["user_id"]
    )
    op.create_index(
        "ix_alert_notifications_created_at", "alert_notifications", ["created_at"]
    )
    op.create_index(
        "ix_alert_notifications_is_read", "alert_notifications", ["is_read"]
    )

    # ── New permissions ───────────────────────────────────────────────────────
    conn = op.get_bind()

    new_perms = [
        ("watchlist", "read", "View watchlists and entries"),
        ("watchlist", "write", "Create, edit, and delete watchlists and entries"),
        ("alert", "read", "View watchlist alerts"),
        ("alert", "write", "Acknowledge, resolve, and dismiss alerts"),
    ]
    perm_ids: dict[str, str] = {}
    for resource, action, desc in new_perms:
        codename = f"{resource}:{action}"
        pid = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO permissions (id, resource, action, description) "
                "VALUES (:id, :resource, :action, :desc) "
                "ON CONFLICT (resource, action) DO NOTHING"
            ),
            {"id": pid, "resource": resource, "action": action, "desc": desc},
        )
        row = conn.execute(
            sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
            {"r": resource, "a": action},
        ).fetchone()
        perm_ids[codename] = str(row[0])

    def _grant(role_name: str, perm_name: str) -> None:
        role_row = conn.execute(
            sa.text("SELECT id FROM roles WHERE name = :n"), {"n": role_name}
        ).fetchone()
        if role_row is None:
            return
        conn.execute(
            sa.text(
                "INSERT INTO role_permissions (role_id, permission_id) "
                "VALUES (:rid, :pid) ON CONFLICT DO NOTHING"
            ),
            {"rid": str(role_row[0]), "pid": perm_ids[perm_name]},
        )

    # Administrator gets everything
    for perm in ("watchlist:read", "watchlist:write", "alert:read", "alert:write"):
        _grant("Administrator", perm)

    # Senior Investigator gets everything
    for perm in ("watchlist:read", "watchlist:write", "alert:read", "alert:write"):
        _grant("Senior Investigator", perm)

    # Investigator gets read-only
    for perm in ("watchlist:read", "alert:read"):
        _grant("Investigator", perm)

    # Analyst gets read-only
    for perm in ("watchlist:read", "alert:read"):
        _grant("Analyst", perm)


def downgrade() -> None:
    op.drop_table("alert_notifications")
    op.drop_table("watchlist_alerts")
    op.drop_table("watchlist_entries")
    op.drop_table("watchlists")
    conn = op.get_bind()
    for resource, action in (("watchlist", "read"), ("watchlist", "write"), ("alert", "read"), ("alert", "write")):
        conn.execute(
            sa.text("DELETE FROM permissions WHERE resource = :r AND action = :a"),
            {"r": resource, "a": action},
        )
