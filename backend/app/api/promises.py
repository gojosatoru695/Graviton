from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.database import get_db
from app.models.promises import Promise

router = APIRouter(prefix="/promises", tags=["promises"])


@router.get("")
def list_promises(
    status: Optional[str] = None,
    promise_type: Optional[str] = None,
    speaker: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    query = db.query(Promise)
    if status and not hasattr(status, "default"):
        query = query.filter(Promise.status == status)
    if promise_type and not hasattr(promise_type, "default"):
        query = query.filter(Promise.promise_type == promise_type)
    if speaker and not hasattr(speaker, "default"):
        query = query.filter(Promise.speaker == speaker)

    promises = query.order_by(Promise.timestamp.desc()).all()
    return [
        {
            "id": p.id,
            "customer_id": p.customer_id,
            "customer_name": p.customer.name if p.customer else "Unknown",
            "order_id": p.order_id,
            "order_number": p.order.order_number if p.order else None,
            "channel": p.channel,
            "timestamp": p.timestamp.isoformat(),
            "speaker": p.speaker,
            "promise_type": p.promise_type,
            "promise_details": p.promise_details,
            "target_date": p.target_date.isoformat() if p.target_date else None,
            "status": p.status,
            "raw_message_snippet": p.raw_message_snippet,
            "confidence_score": float(p.confidence_score),
        }
        for p in promises
    ]
