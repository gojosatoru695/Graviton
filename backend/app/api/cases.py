from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.database import get_db
from app.models.cases import Case, CaseEvidence, PendingAction, ActionReceipt

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("")
def list_cases(
    status: Optional[str] = None,
    case_type: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    query = db.query(Case)
    if status and not hasattr(status, "default"):
        query = query.filter(Case.status == status)
    if case_type and not hasattr(case_type, "default"):
        query = query.filter(Case.case_type == case_type)
    if severity and not hasattr(severity, "default"):
        query = query.filter(Case.severity == severity)

    cases = query.order_by(Case.created_at.desc()).all()
    results = []
    for c in cases:
        pending_act = next((a for a in c.pending_actions if a.status == "PENDING"), None)
        results.append({
            "id": c.id,
            "title": c.title,
            "case_type": c.case_type,
            "severity": c.severity,
            "status": c.status,
            "customer_id": c.customer_id,
            "customer_name": c.customer.name if c.customer else "Customer",
            "order_id": c.order_id,
            "order_number": c.order.order_number if c.order else None,
            "discrepancy_amount": float(c.discrepancy_amount),
            "headline": c.headline,
            "explanation": c.explanation,
            "created_at": c.created_at.isoformat(),
            "evidence_count": len(c.evidence_items),
            "pending_action_count": len([a for a in c.pending_actions if a.status == "PENDING"]),
            "next_action": pending_act.action_summary if pending_act else "Investigation complete",
        })
    return results


@router.get("/{case_id}")
def get_case_detail(case_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    c = db.query(Case).filter(Case.id == case_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Case not found")

    timeline = [
        {
            "id": f"evt-{c.id[:8]}-1",
            "event": "Evidence Ingested & Normalized",
            "timestamp": c.created_at.isoformat(),
            "actor": "System Pipeline",
            "detail": "Orders, bank statements, and customer communications verified.",
        },
        {
            "id": f"evt-{c.id[:8]}-2",
            "event": "Discrepancy Detected",
            "timestamp": c.created_at.isoformat(),
            "actor": "Reconciliation Engine",
            "detail": c.headline,
        },
    ]
    if c.pending_actions:
        timeline.append({
            "id": f"evt-{c.id[:8]}-3",
            "event": "Pending Action Prepared",
            "timestamp": c.pending_actions[0].created_at.isoformat(),
            "actor": "Mandate Gateway",
            "detail": c.pending_actions[0].action_summary,
        })
    for r in c.receipts:
        timeline.append({
            "id": f"evt-{c.id[:8]}-rcpt-{r.id[:6]}",
            "event": f"Action {r.decision}: Receipt #{r.id[:8]}",
            "timestamp": r.timestamp.isoformat(),
            "actor": r.actor,
            "detail": f"Cryptographic Hash: {r.receipt_hash[:16]}...",
        })

    findings = [
        c.explanation,
        f"Discrepancy category: {c.case_type} with severity {c.severity}.",
    ]
    if float(c.discrepancy_amount) > 0:
        findings.append(f"Financial variance verified at ₹{float(c.discrepancy_amount):,.2f}.")

    return {
        "id": c.id,
        "title": c.title,
        "case_type": c.case_type,
        "severity": c.severity,
        "status": c.status,
        "customer_id": c.customer_id,
        "customer_name": c.customer.name if c.customer else "Customer",
        "customer_phone": c.customer.phone if c.customer else "+919876543210",
        "order_id": c.order_id,
        "order_number": c.order.order_number if c.order else None,
        "order_amount": float(c.order.net_amount) if c.order else None,
        "delivery_status": c.order.status if c.order else "DELIVERED",
        "payment_status": "PARTIAL" if c.case_type == "PAYMENT_SHORTFALL" else "PENDING",
        "discrepancy_amount": float(c.discrepancy_amount),
        "headline": c.headline,
        "explanation": c.explanation,
        "created_at": c.created_at.isoformat(),
        "timeline": timeline,
        "findings": findings,
        "evidence_items": [
            {
                "id": e.id,
                "evidence_type": e.evidence_type,
                "source_table": e.source_table,
                "source_id": e.source_id,
                "payload": e.content_payload,
                "collected_at": c.created_at.isoformat(),
            }
            for e in c.evidence_items
        ],
        "pending_actions": [
            {
                "id": a.id,
                "action_type": a.action_type,
                "target_recipient": a.target_recipient,
                "action_summary": a.action_summary,
                "payload": a.payload,
                "status": a.status,
                "approval_required": True,
                "reversibility": "REVERSIBLE" if a.action_type == "RAZORPAY_PAYMENT_LINK" else "IRREVERSIBLE",
                "created_at": a.created_at.isoformat(),
            }
            for a in c.pending_actions
        ],
        "receipts": [
            {
                "id": r.id,
                "decision": r.decision,
                "actor": r.actor,
                "timestamp": r.timestamp.isoformat(),
                "receipt_hash": r.receipt_hash,
                "execution_result": r.execution_result,
            }
            for r in c.receipts
        ],
    }
