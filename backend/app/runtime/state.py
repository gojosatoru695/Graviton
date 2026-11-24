"""
Jarvis Runtime State Specification for LangGraph Agent.
Defines the typed execution state passed between workflow nodes.
"""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class StateTransitionLog(TypedDict):
    """Log entry recording an individual state transition."""
    from_node: str
    to_node: str
    status: str
    timestamp: str
    summary: str


class JarvisState(TypedDict, total=False):
    """
    Complete state payload tracked across the 12-step Jarvis workflow.
    """
    # Run identifiers & lifecycle
    run_id: str
    correlation_id: str
    status: str  # "queued", "running", "investigation_complete", "proposal_prepared", "awaiting_approval", "executing", "verification_pending", "completed", "rejected", "failed"
    current_node: str
    error: Optional[str]

    # Ingestion context
    raw_files: Dict[str, str]  # filename -> content or filepath
    customer_name: Optional[str]
    current_date: str

    # Normalized contract entities (serializable dicts)
    orders: List[Dict[str, Any]]
    invoices: List[Dict[str, Any]]
    bank_transactions: List[Dict[str, Any]]
    settlement_data: Optional[Dict[str, Any]]

    # AI extracted promises & safety evaluation
    promises: List[Dict[str, Any]]
    is_prompt_injection: bool
    injection_reason: Optional[str]

    # Deterministic reconciliation & calculation results
    reconciliation_matches: List[Dict[str, Any]]
    unmatched_items: List[Dict[str, Any]]
    duplicate_groups: List[Dict[str, Any]]
    settlement_variance: Optional[Dict[str, Any]]

    # Case & findings
    case_id: Optional[str]
    case_data: Optional[Dict[str, Any]]
    findings: List[Dict[str, Any]]

    # Action & Approval gate
    action_id: Optional[str]
    approval_id: Optional[str]
    action_proposal: Optional[Dict[str, Any]]
    proposed_payload_hash: Optional[str]
    idempotency_key: Optional[str]
    requires_approval: bool
    approval_decision: Optional[str]  # "APPROVED" or "REJECTED"
    rejection_reason: Optional[str]

    # Execution & audit receipt
    execution_result: Optional[Dict[str, Any]]
    verification_status: Optional[str]
    receipt: Optional[Dict[str, Any]]

    # Output summary & transition audit trail
    output_summary: Optional[str]
    transition_logs: List[StateTransitionLog]
