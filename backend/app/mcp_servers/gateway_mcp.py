from typing import Dict, Any
from fastmcp import FastMCP
from app.database import SessionLocal
from app.models.cases import PendingAction

mcp = FastMCP("Jarvis-Action-Gateway-Server")


@mcp.tool()
def execute_approved_action(action_id: str, human_approval_confirmation: bool) -> Dict[str, Any]:
    """
    Executes a pending action ONLY IF explicit human approval is confirmed.
    Safety Rules:
    - Never executes without human_approval_confirmation == True.
    - Uses Razorpay Test Mode or simulated outbound delivery.
    """
    if not human_approval_confirmation:
        return {"error": "Action execution rejected: Explicit human approval required."}

    from app.services.receipt_service import ReceiptService
    db = SessionLocal()
    try:
        service = ReceiptService(db)
        return service.process_decision(action_id, decision="APPROVED")
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()
