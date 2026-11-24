"""
Unit and Integration Tests for Jarvis LangGraph Agent Runtime.
Verifies the 12-node workflow, checkpointing in database, clean pause at waiting_approval,
resumption after approval, rejection cleanup, execution failure resilience, and model routing.
"""

import os
import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.api.runs import (
    ApprovalDecisionRequest,
    RunResponse,
    StartRunRequest,
    _load_default_demo_files,
    approve_run,
    get_run,
    list_runs,
    reject_run,
    start_run,
)
from app.main import app
from app.runtime.checkpointer import DatabaseCheckpointer
from app.runtime.graph import (
    compiled_graph,
    resume_agent_workflow,
    run_agent_workflow,
)
from app.runtime.nodes import node_execute_approved_action
from app.runtime.router import ModelRouter
from app.runtime.state import JarvisState


@pytest.fixture
def checkpointer():
    return DatabaseCheckpointer()


@pytest.fixture
def test_files():
    return _load_default_demo_files()


# -----------------------------------------------------------------------------
# 1. End-to-End Workflow & HITL Pause Tests
# -----------------------------------------------------------------------------
def test_runtime_stops_cleanly_at_waiting_approval(test_files, checkpointer):
    """
    Verify the 12-node workflow executes from ingest_files up to wait_for_approval,
    stopping cleanly in 'waiting_approval' status with an approval_id and case_id.
    """
    run_id = f"test_run_{uuid.uuid4().hex[:8]}"

    initial_state: JarvisState = {
        "run_id": run_id,
        "correlation_id": run_id,
        "status": "running",
        "current_node": "START",
        "raw_files": test_files,
        "customer_name": "Priya Sharma",
        "current_date": "2024-10-14",
        "orders": [],
        "invoices": [],
        "bank_transactions": [],
        "settlement_data": None,
        "promises": [],
        "reconciliation_matches": [],
        "unmatched_items": [],
        "duplicate_groups": [],
        "findings": [],
        "transition_logs": [],
    }

    state = run_agent_workflow(initial_state)

    # 1. State assertions
    assert state["run_id"] == run_id
    assert state["status"] == "waiting_approval"
    assert state["current_node"] == "wait_for_approval"
    assert state.get("approval_id") is not None
    assert state.get("case_id") is not None
    assert state.get("output_summary") is not None
    assert "1550" in state["output_summary"]  # Hero ₹1,550 settlement residual!

    # 2. Database checkpoint persistence
    persisted = checkpointer.load_checkpoint(run_id)
    assert persisted is not None
    assert persisted["run_id"] == run_id
    assert persisted["status"] == "waiting_approval"
    assert persisted["case_id"] == state["case_id"]
    assert persisted["approval_id"] == state["approval_id"]

    # 3. Transition log verification
    logs = state.get("transition_logs", [])
    assert len(logs) >= 8
    node_names = [l["to_node"] for l in logs]
    assert "ingest_files" in node_names
    assert "normalize_records" in node_names
    assert "reconcile_payments" in node_names
    assert "calculate_settlement_variance" in node_names
    assert "build_case" in node_names
    assert "prepare_action" in node_names
    assert "request_approval" in node_names
    assert "wait_for_approval" in node_names


def test_runtime_resumes_after_seller_approval(test_files, checkpointer):
    """
    Verify that when the seller approves, the workflow resumes from wait_for_approval,
    executes the action, generates an audit receipt, and marks status as completed.
    """
    run_id = f"test_run_appr_{uuid.uuid4().hex[:8]}"

    initial_state: JarvisState = {
        "run_id": run_id,
        "correlation_id": run_id,
        "status": "running",
        "current_node": "START",
        "raw_files": test_files,
        "current_date": "2024-10-14",
    }
    state = run_agent_workflow(initial_state)
    assert state["status"] == "waiting_approval"

    # Resume with approval
    resumed_state = resume_agent_workflow(run_id, decision="APPROVED")

    assert resumed_state is not None
    assert resumed_state["status"] == "completed"
    assert resumed_state["current_node"] == "generate_receipt"
    assert resumed_state.get("receipt") is not None
    receipt = resumed_state["receipt"]
    assert receipt["decision"] == "APPROVED"
    assert receipt["receipt_hash"] is not None
    assert len(receipt["receipt_hash"]) == 64  # SHA-256


def test_runtime_rejection_cleanup_and_audit_receipt(test_files, checkpointer):
    """
    Verify that when the seller rejects the proposed action, the workflow
    runs rejection cleanup, cancels the pending action, and issues a rejection receipt.
    """
    run_id = f"test_run_rej_{uuid.uuid4().hex[:8]}"

    initial_state: JarvisState = {
        "run_id": run_id,
        "correlation_id": run_id,
        "status": "running",
        "current_node": "START",
        "raw_files": test_files,
        "current_date": "2024-10-14",
    }
    state = run_agent_workflow(initial_state)
    assert state["status"] == "waiting_approval"

    # Resume with rejection
    resumed_state = resume_agent_workflow(
        run_id,
        decision="REJECTED",
        rejection_reason="Seller prefers manual communication via phone.",
    )

    assert resumed_state is not None
    assert resumed_state["status"] == "rejected"
    assert resumed_state["current_node"] == "rejection_cleanup"
    assert resumed_state.get("receipt") is not None
    receipt = resumed_state["receipt"]
    assert receipt["decision"] == "REJECTED"
    assert receipt["execution_result"]["rejection_reason"] == "Seller prefers manual communication via phone."
    assert resumed_state["action_proposal"]["status"] == "rejected"


def test_runtime_execution_failure_preserves_evidence():
    """
    Verify that if an action execution fails, status is marked as 'failed',
    the error is captured, and the underlying evidence and findings are preserved.
    """
    failing_state: JarvisState = {
        "run_id": "test_run_fail",
        "correlation_id": "corr_fail",
        "status": "approved",
        "action_proposal": None,  # Will trigger AttributeError in node
        "case_id": "case_123",
        "findings": [{"finding_type": "PRESERVED_FINDING"}],
        "transition_logs": [],
    }

    result = node_execute_approved_action(failing_state)

    assert result["status"] == "failed"
    assert result.get("error") is not None
    assert len(result["findings"]) == 1
    assert result["findings"][0]["finding_type"] == "PRESERVED_FINDING"


# -----------------------------------------------------------------------------
# 2. Model Routing Boundary Tests
# -----------------------------------------------------------------------------
def test_model_router_enforces_ai_and_deterministic_separation():
    """
    Verify ModelRouter allows LLMs only for extraction, drafting, and classification,
    and raises ValueError if calculation or reconciliation tasks are routed to an LLM.
    """
    # Allowed tasks
    assert ModelRouter.get_model_for_task("extraction") is not None
    assert ModelRouter.get_model_for_task("drafting") is not None
    assert ModelRouter.get_model_for_task("classification") is not None

    # Forbidden tasks (strict policy violation)
    with pytest.raises(ValueError) as exc1:
        ModelRouter.get_model_for_task("reconciliation")
    assert "Policy Violation" in str(exc1.value)

    with pytest.raises(ValueError) as exc2:
        ModelRouter.get_model_for_task("settlement_variance")
    assert "Policy Violation" in str(exc2.value)

    with pytest.raises(ValueError) as exc3:
        ModelRouter.get_model_for_task("calculations")
    assert "Policy Violation" in str(exc3.value)


# -----------------------------------------------------------------------------
# 3. Runs API Endpoint Integration Tests
# -----------------------------------------------------------------------------
def test_api_runs_workflow_endpoints():
    """
    Verify POST /api/runs, GET /api/runs/{id}, POST /api/runs/{id}/approve, POST /api/runs/{id}/reject
    return the exact RunResponse schema required by the user specification.
    """
    # 1. Start run via API endpoint
    req = StartRunRequest(current_date="2024-10-14")
    run_resp = start_run(req)

    # Exact schema validation
    assert isinstance(run_resp, RunResponse)
    assert run_resp.run_id is not None
    assert run_resp.case_id is not None
    assert run_resp.status == "waiting_approval"
    assert run_resp.output_summary is not None
    assert run_resp.approval_id is not None

    run_id = run_resp.run_id

    # 2. Inspect run via GET endpoint
    run_detail = get_run(run_id)
    assert run_detail["run_id"] == run_id
    assert run_detail["status"] == "waiting_approval"
    assert len(run_detail["transition_logs"]) >= 8

    # 3. Approve run via POST /approve endpoint
    appr_resp = approve_run(run_id)
    assert isinstance(appr_resp, RunResponse)
    assert appr_resp.run_id == run_id
    assert appr_resp.status == "completed"

    # 4. Verify receipt generated
    detail_after_appr = get_run(run_id)
    assert detail_after_appr["receipt"]["decision"] == "APPROVED"
    assert detail_after_appr["receipt"]["receipt_hash"] is not None

    # 5. List runs includes this run
    all_runs = list_runs()
    assert any(r["run_id"] == run_id for r in all_runs)
