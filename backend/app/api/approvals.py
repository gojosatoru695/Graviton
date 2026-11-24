"""
FastAPI Router for Human-in-the-Loop (HITL) Approvals and Cryptographic Receipts.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cases import Case, CaseEvidence, PendingAction, ActionReceipt
from app.policy.kernel import PolicyKernel
from app.services.receipt_service import ReceiptService

router = APIRouter(prefix="/approvals", tags=["Approvals & Policy Gate"])
policy_kernel = PolicyKernel()


# -----------------------------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------------------------
class DecisionPayload(BaseModel):
    decision: str = Field(..., description="'APPROVED' or 'REJECTED'")
    decision_note: Optional[str] = Field(None, description="Optional note or explanation for the decision.")
    actor_id: Optional[str] = Field("seller_manual_hitl", description="Identifier of the approving actor.")


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.get("/pending", response_model=List[Dict[str, Any]])
def list_pending_approvals(db: Session = Depends(get_db)):
    """
    Lists all pending commercial actions awaiting seller approval with full policy evaluation.
    """
    actions = db.query(PendingAction).filter(PendingAction.status == "PENDING").all()

    result = []
    for a in actions:
        ev_items = db.query(CaseEvidence).filter(CaseEvidence.case_id == a.case_id).all()
        ev_ids = [e.id for e in ev_items]

        # Run policy kernel check
        eval_res = policy_kernel.evaluate_action(
            action_type=a.action_type,
            target_recipient=a.target_recipient,
            amount=a.payload.get("amount") if isinstance(a.payload, dict) else None,
            evidence_ids=ev_ids or ["evi_default"],
        )

        result.append({
            "action_id": a.id,
            "case_id": a.case_id,
            "action_type": a.action_type,
            "target_recipient": a.target_recipient,
            "action_summary": a.action_summary,
            "payload": a.payload,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
            "policy_evaluation": {
                "is_allowed": eval_res.is_allowed,
                "requires_approval": eval_res.requires_human_approval,
                "violations": eval_res.violations,
                "checks": eval_res.policy_checks,
            },
            "evidence_ids": ev_ids,
        })
    return result


@router.post("/{action_id}/decide", response_model=Dict[str, Any])
def decide_action(
    action_id: str,
    payload: DecisionPayload,
    db: Session = Depends(get_db)
):
    """
    Processes human approval or rejection.
    If approved: executes the action and creates an immutable receipt.
    If rejected: performs rejection cleanup and creates an immutable rejection receipt.
    """
    receipt_service = ReceiptService(db, policy_kernel=policy_kernel)
    try:
        receipt = receipt_service.process_decision(
            action_id=action_id,
            decision=payload.decision.upper(),
            actor_id=payload.actor_id or "seller_manual_hitl",
            decision_note=payload.decision_note,
        )
        return receipt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/receipts", response_model=List[Dict[str, Any]])
def list_receipts(db: Session = Depends(get_db)):
    """
    Lists all cryptographic audit receipts in chronological order.
    """
    receipts = db.query(ActionReceipt).order_by(ActionReceipt.timestamp.desc()).all()
    return [
        {
            "receipt_id": r.id,
            "case_id": r.case_id,
            "action_id": r.pending_action_id,
            "decision": r.decision,
            "actor_id": r.actor,
            "created_at": r.timestamp.isoformat(),
            "immutable_hash": r.receipt_hash,
            "previous_hash": r.tamper_chain_previous_hash,
            "payload_snapshot": r.payload_snapshot,
            "execution_result": r.execution_result,
        }
        for r in receipts
    ]


@router.get("/verify-chain", response_model=Dict[str, Any])
def verify_receipt_chain(db: Session = Depends(get_db)):
    """
    Audits the entire receipt ledger and verifies SHA-256 chain integrity.
    """
    receipt_service = ReceiptService(db)
    return receipt_service.verify_receipt_chain()
