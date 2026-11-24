import hashlib
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database import get_db
from app.models.cases import ActionReceipt
from app.services.receipt_service import compute_canonical_receipt_hash, ReceiptService

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.get("")
def list_receipts(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    receipts = db.query(ActionReceipt).order_by(ActionReceipt.timestamp.desc()).all()
    results = []
    for r in receipts:
        act = r.pending_action
        act_type = act.action_type if act else "COMMERCIAL_ACTION"
        evi_ids = [e.id for e in r.case.evidence_items] if r.case else []
        results.append({
            "id": r.id,
            "pending_action_id": r.pending_action_id,
            "case_id": r.case_id,
            "case_title": r.case.title if r.case else "Unknown Case",
            "action_type": act_type,
            "evidence_used": evi_ids,
            "decision": r.decision,
            "actor": r.actor,
            "timestamp": r.timestamp.isoformat(),
            "payload_snapshot": r.payload_snapshot,
            "execution_result": r.execution_result,
            "receipt_hash": r.receipt_hash,
            "tamper_chain_previous_hash": r.tamper_chain_previous_hash,
        })
    return results


@router.get("/{receipt_id}/verify")
def verify_receipt(receipt_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    receipt = db.query(ActionReceipt).filter(ActionReceipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    timestamp_str = receipt.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(receipt.timestamp, "strftime") else str(receipt.timestamp)
    prev_hash = receipt.tamper_chain_previous_hash or ReceiptService.GENESIS_HASH

    computed_hash = compute_canonical_receipt_hash(
        receipt_id=receipt.id,
        action_id=receipt.pending_action_id,
        case_id=receipt.case_id or "",
        decision=receipt.decision,
        actor=receipt.actor,
        timestamp_str=timestamp_str,
        payload_snapshot=receipt.payload_snapshot,
        execution_result=receipt.execution_result,
        previous_hash=prev_hash,
    )
    is_valid = (computed_hash == receipt.receipt_hash)

    return {
        "receipt_id": receipt.id,
        "is_valid": is_valid,
        "stored_hash": receipt.receipt_hash,
        "computed_hash": computed_hash,
        "timestamp": receipt.timestamp.isoformat(),
        "actor": receipt.actor,
        "decision": receipt.decision,
    }


@router.get("/verify-chain")
def verify_receipt_chain(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Audits the entire receipt ledger and verifies SHA-256 chain integrity.
    """
    receipt_service = ReceiptService(db)
    return receipt_service.verify_receipt_chain()
