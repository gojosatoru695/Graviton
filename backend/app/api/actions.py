from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from app.database import get_db
from app.models.cases import PendingAction
from app.schemas.contracts import ActionDecisionRequest
from app.services.receipt_service import ReceiptService

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("/pending")
def get_pending_actions(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    actions = db.query(PendingAction).filter(PendingAction.status == "PENDING").all()
    return [
        {
            "id": a.id,
            "case_id": a.case_id,
            "action_type": a.action_type,
            "target_recipient": a.target_recipient,
            "action_summary": a.action_summary,
            "payload": a.payload,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
        }
        for a in actions
    ]


@router.post("/{action_id}/decision")
def decide_action(
    action_id: str,
    req: ActionDecisionRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    service = ReceiptService(db)
    try:
        result = service.process_decision(
            action_id=action_id,
            decision=req.decision.value,
            actor="Seller (Manual HITL)",
            rejection_reason=req.rejection_reason
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
