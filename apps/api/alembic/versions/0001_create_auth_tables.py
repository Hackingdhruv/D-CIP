"""Create auth tables and seed initial data.

Revision ID: 0001
Revises: None
Create Date: 2026-06-26
"""

from __future__ import annotations

import uuid

import bcrypt
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Tables
    # -------------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_roles_slug", "roles", ["slug"], unique=True)
    op.create_index("uq_roles_name", "roles", ["name"], unique=True)

    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("resource", "action", name="uq_permissions_resource_action"),
    )
    op.create_index("ix_permissions_resource", "permissions", ["resource"])

    op.create_table(
        "user_roles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "assigned_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )

    op.create_table(
        "role_permissions",
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "permission_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("jti", sa.String(255), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
    )
    op.create_index("ix_refresh_tokens_jti", "refresh_tokens", ["jti"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_is_revoked", "refresh_tokens", ["is_revoked"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
    )
    op.create_index(
        "ix_password_reset_tokens_token_hash",
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_token", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_user_sessions_session_token", "user_sessions", ["session_token"], unique=True
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_is_active", "user_sessions", ["is_active"])

    op.create_table(
        "auth_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_auth_audit_events_user_id", "auth_audit_events", ["user_id"])
    op.create_index("ix_auth_audit_events_event_type", "auth_audit_events", ["event_type"])
    op.create_index("ix_auth_audit_events_created_at", "auth_audit_events", ["created_at"])

    # -------------------------------------------------------------------------
    # Seed roles
    # -------------------------------------------------------------------------
    bind = op.get_bind()

    role_ids: dict[str, str] = {
        "administrator": str(uuid.uuid4()),
        "senior_investigator": str(uuid.uuid4()),
        "investigator": str(uuid.uuid4()),
        "analyst": str(uuid.uuid4()),
        "read_only": str(uuid.uuid4()),
    }

    roles = [
        {
            "id": role_ids["administrator"],
            "name": "Administrator",
            "slug": "administrator",
            "description": "Full platform control, user and system administration.",
            "is_system": True,
        },
        {
            "id": role_ids["senior_investigator"],
            "name": "Senior Investigator",
            "slug": "senior_investigator",
            "description": "Leads cases, manages teams, approves reports.",
            "is_system": True,
        },
        {
            "id": role_ids["investigator"],
            "name": "Investigator",
            "slug": "investigator",
            "description": "Works cases, manages evidence and findings.",
            "is_system": True,
        },
        {
            "id": role_ids["analyst"],
            "name": "Analyst",
            "slug": "analyst",
            "description": "Analyzes evidence and contributes findings.",
            "is_system": True,
        },
        {
            "id": role_ids["read_only"],
            "name": "Read Only",
            "slug": "read_only",
            "description": "Views assigned cases without making changes.",
            "is_system": True,
        },
    ]
    for r in roles:
        bind.execute(
            sa.text(
                "INSERT INTO roles (id, name, slug, description, is_system) "
                "VALUES (:id, :name, :slug, :description, :is_system)"
            ),
            r,
        )

    # -------------------------------------------------------------------------
    # Seed permissions
    # -------------------------------------------------------------------------
    _permissions = [
        ("case", "read", "Read cases"),
        ("case", "create", "Create cases"),
        ("case", "update", "Update cases"),
        ("case", "delete", "Delete cases"),
        ("case", "assign", "Assign cases"),
        ("evidence", "read", "Read evidence"),
        ("evidence", "upload", "Upload evidence"),
        ("evidence", "delete", "Delete evidence"),
        ("report", "read", "Read reports"),
        ("report", "create", "Create reports"),
        ("report", "publish", "Publish reports"),
        ("ai", "run", "Run AI analysis"),
        ("ai", "review", "Review AI results"),
        ("user", "manage", "Manage users, roles, permissions"),
        ("audit", "read", "Read audit logs"),
        ("settings", "manage", "Manage platform settings"),
    ]

    perm_ids: dict[str, str] = {}
    for resource, action, description in _permissions:
        pid = str(uuid.uuid4())
        perm_ids[f"{resource}:{action}"] = pid
        bind.execute(
            sa.text(
                "INSERT INTO permissions (id, resource, action, description) "
                "VALUES (:id, :resource, :action, :description)"
            ),
            {"id": pid, "resource": resource, "action": action, "description": description},
        )

    # -------------------------------------------------------------------------
    # Seed role_permissions (mirrors packages/shared/src/rbac.ts)
    # -------------------------------------------------------------------------
    _role_permissions: dict[str, list[str]] = {
        "administrator": list(perm_ids.keys()),
        "senior_investigator": [
            "case:read", "case:create", "case:update", "case:delete", "case:assign",
            "evidence:read", "evidence:upload", "evidence:delete",
            "report:read", "report:create", "report:publish",
            "ai:run", "ai:review", "audit:read",
        ],
        "investigator": [
            "case:read", "case:create", "case:update",
            "evidence:read", "evidence:upload",
            "report:read", "report:create",
            "ai:run", "ai:review",
        ],
        "analyst": [
            "case:read",
            "evidence:read", "evidence:upload",
            "report:read",
            "ai:run", "ai:review",
        ],
        "read_only": [
            "case:read", "evidence:read", "report:read",
        ],
    }

    for role_slug, perms in _role_permissions.items():
        for perm_codename in perms:
            bind.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) "
                    "VALUES (:role_id, :permission_id)"
                ),
                {
                    "role_id": role_ids[role_slug],
                    "permission_id": perm_ids[perm_codename],
                },
            )

    # -------------------------------------------------------------------------
    # Seed default admin user
    # -------------------------------------------------------------------------
    admin_password = "Admin@dcip.2024!"
    admin_hash = bcrypt.hashpw(admin_password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode(
        "utf-8"
    )
    admin_id = str(uuid.uuid4())
    bind.execute(
        sa.text(
            "INSERT INTO users (id, email, username, full_name, password_hash, is_active) "
            "VALUES (:id, :email, :username, :full_name, :password_hash, true)"
        ),
        {
            "id": admin_id,
            "email": "admin@dcip.local",
            "username": "admin",
            "full_name": "System Administrator",
            "password_hash": admin_hash,
        },
    )
    bind.execute(
        sa.text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"),
        {"user_id": admin_id, "role_id": role_ids["administrator"]},
    )


def downgrade() -> None:
    op.drop_table("auth_audit_events")
    op.drop_table("user_sessions")
    op.drop_table("password_reset_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
