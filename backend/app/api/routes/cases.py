from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import SupportCase, AuditLog

router = APIRouter()


@router.get("/cases")
def cases(db: Session = Depends(get_db)):
    rows = db.query(SupportCase).order_by(SupportCase.created_at.desc()).all()
    return [
        {
            "case_id": x.case_id,
            "customer_id": x.customer_id,
            "message": x.message,
            "intent": x.intent,
            "status": x.status,
            "resolution": x.resolution,
            "escalation_reason": x.escalation_reason,
            "created_at": x.created_at,
        }
        for x in rows
    ]


@router.get("/cases/{case_id}/audit")
def audit_trail(case_id: str, db: Session = Depends(get_db)):
    rows = db.query(AuditLog).filter_by(case_id=case_id).order_by(AuditLog.created_at).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Case not found")
    return [
        {
            "event_type": x.event_type,
            "details": x.details,
            "created_at": x.created_at,
        }
        for x in rows
    ]
