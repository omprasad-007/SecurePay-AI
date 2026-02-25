from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..deps import Principal
from ..models import AuditLog


def write_audit_log(
    db: Session,
    principal: Principal,
    action_type: str,
    entity_type: str,
    entity_id: str,
    ip_address: str,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        details=details or {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
