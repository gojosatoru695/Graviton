from typing import Dict, Any, List, Optional
from fastmcp import FastMCP
from app.database import SessionLocal
from app.models.cases import Case, CaseEvidence, ActionReceipt
from app.models.promises import Promise

mcp = FastMCP("Jarvis-Evidence-Server")


@mcp.tool()
def get_case_evidence(case_id: str) -> Dict[str, Any]:
    """Retrieves full evidence chain and narrative for a given case ID."""
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {"error": f"Case not found: {case_id}"}
        
        evidence = db.query(CaseEvidence).filter(CaseEvidence.case_id == case_id).all()
        return {
            "case_id": case.id,
            "title": case.title,
            "headline": case.headline,
            "explanation": case.explanation,
            "discrepancy_amount": float(case.discrepancy_amount),
            "evidence_items": [
                {
                    "id": e.id,
                    "type": e.evidence_type,
                    "table": e.source_table,
                    "payload": e.content_payload,
                }
                for e in evidence
            ]
        }
    finally:
        db.close()


@mcp.tool()
def verify_receipt_hash(receipt_id: str) -> Dict[str, Any]:
    """Cryptographically verifies an immutable action receipt hash."""
    import hashlib
    import json
    db = SessionLocal()
    try:
        receipt = db.query(ActionReceipt).filter(ActionReceipt.id == receipt_id).first()
        if not receipt:
            return {"error": f"Receipt not found: {receipt_id}"}

        # Recompute hash
        hasher = hashlib.sha256()
        hasher.update(receipt.pending_action_id.encode("utf-8"))
        hasher.update(receipt.decision.encode("utf-8"))
        hasher.update(receipt.timestamp.isoformat().encode("utf-8"))
        hasher.update(json.dumps(receipt.payload_snapshot, sort_keys=True).encode("utf-8"))
        hasher.update(json.dumps(receipt.execution_result, sort_keys=True).encode("utf-8"))
        if receipt.tamper_chain_previous_hash:
            hasher.update(receipt.tamper_chain_previous_hash.encode("utf-8"))

        expected_hash = hasher.hexdigest()
        is_valid = (expected_hash == receipt.receipt_hash)

        return {
            "receipt_id": receipt.id,
            "is_valid": is_valid,
            "stored_hash": receipt.receipt_hash,
            "computed_hash": expected_hash,
            "timestamp": receipt.timestamp.isoformat(),
            "actor": receipt.actor,
            "decision": receipt.decision,
        }
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()
