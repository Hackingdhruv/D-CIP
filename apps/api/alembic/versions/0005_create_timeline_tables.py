"""Create the investigation timeline engine tables + permissions.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-26

Adds:
  - timeline_events           — the canonical, curated investigation timeline
  - timeline_event_comments   — investigator commentary on events
  - timeline:read/write/manage permissions, granted to the existing roles
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── timeline_events ────────────────────────────────────────────────────────
    op.create_table(
        "timeline_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidence.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("origin_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("event_type", sa.String(40), nullable=False, server_default="unknown"),
        sa.Column("category", sa.String(30), nullable=False, server_default="custom"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_end_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone_name", sa.String(60), nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.8"),
        sa.Column(
            "verification_status",
            sa.String(20),
            nullable=False,
            server_default="unverified",
        ),
        sa.Column("is_pinned", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_bookmarked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_merged", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "merged_into_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("timeline_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "entities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("location", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "attachments",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("source_text", sa.Text, nullable=True),
        sa.Column("source_reference", sa.String(500), nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_timeline_events_case_id", "timeline_events", ["case_id"])
    op.create_index("ix_timeline_events_evidence_id", "timeline_events", ["evidence_id"])
    op.create_index(
        "ix_timeline_events_origin_event_id", "timeline_events", ["origin_event_id"]
    )
    op.create_index("ix_timeline_events_source_type", "timeline_events", ["source_type"])
    op.create_index("ix_timeline_events_event_type", "timeline_events", ["event_type"])
    op.create_index("ix_timeline_events_category", "timeline_events", ["category"])
    op.create_index(
        "ix_timeline_events_event_timestamp", "timeline_events", ["event_timestamp"]
    )
    op.create_index(
        "ix_timeline_events_verification_status",
        "timeline_events",
        ["verification_status"],
    )
    op.create_index("ix_timeline_events_is_pinned", "timeline_events", ["is_pinned"])
    op.create_index(
        "ix_timeline_events_merged_into_id", "timeline_events", ["merged_into_id"]
    )
    op.create_index("ix_timeline_events_created_at", "timeline_events", ["created_at"])
    # Compound index for the most common query: a case's events in time order.
    op.create_index(
        "ix_timeline_events_case_ts",
        "timeline_events",
        ["case_id", "event_timestamp"],
    )

    # ── timeline_event_comments ────────────────────────────────────────────────
    op.create_table(
        "timeline_event_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("timeline_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("body", sa.Text, nullable=False),
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
        "ix_timeline_event_comments_event_id",
        "timeline_event_comments",
        ["event_id"],
    )

    _seed_permissions()


def _seed_permissions() -> None:
    """Seed timeline permissions and grant them to the standard roles."""
    bind = op.get_bind()

    new_perms = [
        ("timeline", "read", "Read the investigation timeline"),
        ("timeline", "write", "Create and edit timeline events"),
        ("timeline", "manage", "Merge, split, verify and delete timeline events"),
    ]
    perm_ids: dict[str, str] = {}
    for resource, action, description in new_perms:
        pid = str(uuid.uuid4())
        perm_ids[f"{resource}:{action}"] = pid
        bind.execute(
            sa.text(
                "INSERT INTO permissions (id, resource, action, description) "
                "VALUES (:id, :resource, :action, :description)"
            ),
            {"id": pid, "resource": resource, "action": action, "description": description},
        )

    # role slug -> timeline permissions granted (mirrors packages/shared/src/rbac.ts)
    grants: dict[str, list[str]] = {
        "administrator": ["timeline:read", "timeline:write", "timeline:manage"],
        "senior_investigator": ["timeline:read", "timeline:write", "timeline:manage"],
        "investigator": ["timeline:read", "timeline:write"],
        "analyst": ["timeline:read", "timeline:write"],
        "read_only": ["timeline:read"],
    }
    for role_slug, codenames in grants.items():
        role_row = bind.execute(
            sa.text("SELECT id FROM roles WHERE slug = :slug"), {"slug": role_slug}
        ).first()
        if not role_row:
            continue
        for codename in codenames:
            bind.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "VALUES (:role_id, :permission_id)"
                ),
                {"role_id": role_row[0], "permission_id": perm_ids[codename]},
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM permissions WHERE resource = 'timeline' "
            "AND action IN ('read', 'write', 'manage')"
        )
    )
    op.drop_table("timeline_event_comments")
    op.drop_table("timeline_events")
