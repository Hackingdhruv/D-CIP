"""ORM models package.

Import all models here so Alembic autogenerate can discover them through
``app.db.base.Base.metadata``.
"""

from app.models.associations import role_permissions, user_roles
from app.models.auth_audit_event import AuthAuditEvent
from app.models.case import Case
from app.models.case_activity import CaseActivity
from app.models.case_assignment import CaseAssignment
from app.models.case_note import CaseNote
from app.models.case_summary import CaseSummary
from app.models.case_task import CaseTask
from app.models.evidence import Evidence
from app.models.evidence_custody import EvidenceCustodyEvent
from app.models.evidence_entity import EvidenceEntity
from app.models.evidence_keyword import EvidenceKeyword
from app.models.evidence_summary import EvidenceSummary
from app.models.evidence_timeline_event import EvidenceTimelineEvent
from app.models.timeline_event import TimelineEvent
from app.models.timeline_event_comment import TimelineEventComment
from app.models.ai_chat_message import AiChatMessage
from app.models.report import InvestigationReport, ReportExport
from app.models.system_config import SystemConfig
from app.models.watchlist import Watchlist, WatchlistEntry
from app.models.watchlist_alert import WatchlistAlert
from app.models.alert_notification import AlertNotification
from app.models.password_reset_token import PasswordResetToken
from app.models.permission import Permission
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User
from app.models.user_session import UserSession

__all__ = [
    "User",
    "Role",
    "Permission",
    "user_roles",
    "role_permissions",
    "RefreshToken",
    "PasswordResetToken",
    "UserSession",
    "AuthAuditEvent",
    "Case",
    "CaseAssignment",
    "CaseActivity",
    "CaseTask",
    "CaseNote",
    "CaseSummary",
    "Evidence",
    "EvidenceCustodyEvent",
    "EvidenceEntity",
    "EvidenceKeyword",
    "EvidenceTimelineEvent",
    "EvidenceSummary",
    "TimelineEvent",
    "TimelineEventComment",
    "AiChatMessage",
    "InvestigationReport",
    "ReportExport",
    "SystemConfig",
    "Watchlist",
    "WatchlistEntry",
    "WatchlistAlert",
    "AlertNotification",
]
