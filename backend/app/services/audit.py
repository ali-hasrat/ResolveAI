import json
from sqlalchemy.orm import Session
from app.models.models import AuditLog


def audit(db: Session, case_id: str, event_type: str, details):
    db.add(
        AuditLog(
            case_id=case_id,
            event_type=event_type,
            details=json.dumps(details, default=str),
        )
    )
    db.commit()
