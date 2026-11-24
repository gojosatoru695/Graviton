"""
Jarvis Runtime Checkpointer & Database State Persistence.
Saves, loads, and manages workflow state transitions in SQLite/SQLAlchemy.

Rules:
- Full state snapshot preserved at every node transition.
- Enables runs to be stopped at 'waiting_approval' and cleanly resumed.
- Thread-safe database transactions.
"""

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, String, Text, JSON, create_engine
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.runtime.state import JarvisState


def _serialize_for_db(obj: Any) -> Any:
    """Recursively converts Decimals and datetimes into JSON-serializable primitives."""
    if isinstance(obj, Decimal):
        return str(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize_for_db(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_db(x) for x in obj]
    return obj


class AgentRunRecord(Base):
    """
    SQLAlchemy model persisting the execution state and checkpoint history of an agent run.
    """
    __tablename__ = "agent_runs"

    run_id = Column(String(64), primary_key=True)
    correlation_id = Column(String(64), nullable=False)
    case_id = Column(String(64), nullable=True)
    approval_id = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="running")
    current_node = Column(String(64), nullable=False, default="START")
    state_json = Column(JSON, nullable=False)
    output_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


# Ensure table creation in the active database
Base.metadata.create_all(bind=engine, tables=[AgentRunRecord.__table__])


class DatabaseCheckpointer:
    """
    Service for persisting and restoring JarvisState across execution checkpoints.
    """

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def save_checkpoint(self, state: JarvisState, current_node: str) -> None:
        """
        Saves or updates a run state checkpoint in the database.
        """
        run_id = state.get("run_id", "default_run")
        correlation_id = state.get("correlation_id", run_id)
        case_id = state.get("case_id")
        approval_id = state.get("approval_id")
        status = state.get("status", "running")
        output_summary = state.get("output_summary")

        serialized_state = _serialize_for_db(dict(state))

        with self.session_factory() as session:
            record = session.query(AgentRunRecord).filter(AgentRunRecord.run_id == run_id).first()
            if not record:
                record = AgentRunRecord(
                    run_id=run_id,
                    correlation_id=correlation_id,
                    case_id=case_id,
                    approval_id=approval_id,
                    status=status,
                    current_node=current_node,
                    state_json=serialized_state,
                    output_summary=output_summary,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                session.add(record)
            else:
                record.case_id = case_id or record.case_id
                record.approval_id = approval_id or record.approval_id
                record.status = status
                record.current_node = current_node
                record.state_json = serialized_state
                record.output_summary = output_summary or record.output_summary
                record.updated_at = datetime.now(timezone.utc)

            session.commit()

    def load_checkpoint(self, run_id: str) -> Optional[JarvisState]:
        """
        Retrieves the latest state snapshot for a given run_id.
        """
        with self.session_factory() as session:
            record = session.query(AgentRunRecord).filter(AgentRunRecord.run_id == run_id).first()
            if not record:
                return None

            state_dict = dict(record.state_json)
            # Ensure latest status and node are reflected
            state_dict["status"] = record.status
            state_dict["current_node"] = record.current_node
            state_dict["case_id"] = record.case_id
            state_dict["approval_id"] = record.approval_id
            state_dict["output_summary"] = record.output_summary
            return JarvisState(**state_dict)

    def record_approval_decision(
        self,
        run_id: str,
        decision: str,
        rejection_reason: Optional[str] = None
    ) -> Optional[JarvisState]:
        """
        Records the micro-business owner's decision (APPROVED / REJECTED)
        and prepares the state for resumption.
        """
        state = self.load_checkpoint(run_id)
        if not state:
            return None

        state["approval_decision"] = decision
        if rejection_reason:
            state["rejection_reason"] = rejection_reason

        new_status = "approved" if decision == "APPROVED" else "rejected"
        state["status"] = new_status

        self.save_checkpoint(state, current_node="wait_for_approval")
        return state

    def list_all_runs(self) -> List[Dict[str, Any]]:
        """
        Returns summary of all recorded runs.
        """
        with self.session_factory() as session:
            records = session.query(AgentRunRecord).order_by(AgentRunRecord.created_at.desc()).all()
            return [
                {
                    "run_id": r.run_id,
                    "case_id": r.case_id,
                    "approval_id": r.approval_id,
                    "status": r.status,
                    "current_node": r.current_node,
                    "output_summary": r.output_summary,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in records
            ]
