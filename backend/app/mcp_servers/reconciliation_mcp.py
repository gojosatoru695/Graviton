from typing import Dict, Any, List
from fastmcp import FastMCP
from app.database import SessionLocal
from app.engines.reconciler import ReconciliationEngine
from app.engines.variance import VarianceEngine

mcp = FastMCP("Jarvis-Reconciliation-Server")


@mcp.tool()
def reconcile_payments() -> Dict[str, Any]:
    """Runs deterministic payment reconciliation between bank credits and orders."""
    db = SessionLocal()
    try:
        engine = ReconciliationEngine(db)
        return engine.run_reconciliation()
    finally:
        db.close()


@mcp.tool()
def calculate_settlement_variance(settlement_id: str) -> Dict[str, Any]:
    """Calculates deterministic deduction waterfall and unexplained residual for a marketplace settlement."""
    db = SessionLocal()
    try:
        engine = VarianceEngine(db)
        return engine.analyze_settlement(settlement_id)
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()
