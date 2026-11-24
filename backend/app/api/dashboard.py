from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Dict, Any

from app.database import get_db
from app.models.entities import Order, BankTransaction, SettlementReport
from app.models.cases import Case, PendingAction
from app.models.promises import Promise
from app.config import settings

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Provides daily overview metrics for the Today screen."""
    open_cases = db.query(Case).filter(Case.status.in_(["OPEN", "PENDING_APPROVAL", "NEEDS_APPROVAL"])).all()
    pending_actions = db.query(PendingAction).filter(PendingAction.status == "PENDING").all()
    broken_promises = db.query(Promise).filter(Promise.status.in_(["BROKEN", "OVERDUE"])).all()
    unrecorded_gifts = db.query(Promise).filter(Promise.status == "UNRECORDED").all()
    unmatched_txns = db.query(BankTransaction).filter(BankTransaction.reconciliation_status == "UNMATCHED").all()
    
    # Calculate total unpaid order discrepancy
    total_shortfall = sum(float(c.discrepancy_amount) for c in open_cases if c.case_type == "PAYMENT_SHORTFALL")
    total_variance = sum(float(c.discrepancy_amount) for c in open_cases if c.case_type in ["MARKETPLACE_VARIANCE", "SETTLEMENT_VARIANCE"])
    
    # Urgent attention items (top 5 by severity)
    urgent_cases = sorted(
        open_cases,
        key=lambda x: (0 if x.severity == "CRITICAL" else (1 if x.severity == "HIGH" else 2))
    )[:5]

    return {
        "watermark": settings.DATASET_WATERMARK,
        "metrics": {
            "uncollected_balance": total_shortfall,
            "marketplace_variance": total_variance,
            "broken_promises": len(broken_promises),
            "pending_approvals": len(pending_actions),
            "unmatched_payments": len(unmatched_txns),
            "total_open_cases": len(open_cases),
            "cases_needing_attention": len(open_cases),
            # Legacy alias keys
            "uncollected_balance_inr": total_shortfall,
            "marketplace_variance_inr": total_variance,
            "pending_approvals_count": len(pending_actions),
            "broken_promises_count": len(broken_promises),
            "unrecorded_promises_count": len(unrecorded_gifts),
        },
        "urgent_cases": [
            {
                "id": c.id,
                "title": c.title,
                "case_type": c.case_type,
                "severity": c.severity,
                "discrepancy_amount": float(c.discrepancy_amount),
                "headline": c.headline,
                "status": c.status,
                "order_number": c.order.order_number if c.order else None,
            }
            for c in urgent_cases
        ]
    }
