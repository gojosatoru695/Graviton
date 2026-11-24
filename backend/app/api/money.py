from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from app.database import get_db
from app.models.entities import Order, BankTransaction, SettlementReport
from app.engines.reconciler import ReconciliationEngine
from app.engines.variance import VarianceEngine

router = APIRouter(prefix="/money", tags=["money"])


@router.get("/reconciliation")
def get_reconciliation_overview(db: Session = Depends(get_db)) -> Dict[str, Any]:
    engine = ReconciliationEngine(db)
    result = engine.run_reconciliation()
    
    # Also fetch recent bank transactions with their reconciliation status
    txns = db.query(BankTransaction).order_by(BankTransaction.transaction_date.desc()).limit(50).all()
    orders = db.query(Order).all()
    
    total_received = sum(float(t.amount) for t in txns)
    total_expected = sum(float(o.net_amount) for o in orders)
    
    return {
        "summary": {
            "total_credits": result["total_transactions"],
            "total_amount_received": total_received,
            "expected_amount": total_expected,
            "matched_credits": result["matched_count"],
            "partial_credits": result["partial_count"],
            "duplicate_candidates": result["duplicate_candidates_count"],
            "unmatched_credits": result["unmatched_count"],
        },
        "expected_vs_received": {
            "expected": total_expected,
            "received": total_received,
            "variance": total_expected - total_received,
        },
        "partials": result["partials"],
        "duplicates": result["duplicates"],
        "transactions": [
            {
                "id": t.id,
                "date": t.transaction_date.isoformat(),
                "type": t.transaction_type,
                "amount": float(t.amount),
                "utr": t.utr_reference,
                "sender": t.sender_name or "Direct Deposit",
                "upi_id": t.sender_upi_id,
                "description": t.raw_description,
                "status": t.reconciliation_status,
                "matched_order_id": t.matched_order_id,
                "matched_order": t.matched_order.order_number if t.matched_order else None,
            }
            for t in txns
        ]
    }


@router.get("/settlements")
def get_settlements_overview(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    engine = VarianceEngine(db)
    return engine.analyze_all_settlements()
