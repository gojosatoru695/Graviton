"""
Jarvis LangGraph Agent Workflow Graph Definition.
Wires the 12 explicit processing nodes into a compiled, checkpointed StateGraph.
"""

from typing import Any, Dict, Optional
from langgraph.graph import StateGraph, START, END

from app.runtime.checkpointer import DatabaseCheckpointer
from app.runtime.nodes import (
    node_build_case,
    node_calculate_settlement_variance,
    node_execute_approved_action,
    node_extract_promises,
    node_generate_findings,
    node_generate_receipt,
    node_ingest_files,
    node_normalize_records,
    node_prepare_action,
    node_reconcile_payments,
    node_rejection_cleanup,
    node_request_approval,
    node_verify_provider_operation,
    node_wait_for_approval,
)
from app.runtime.router import (
    route_after_request_approval,
    route_after_wait_for_approval,
    route_from_start,
)
from app.runtime.state import JarvisState

checkpointer = DatabaseCheckpointer()


def create_jarvis_graph():
    """
    Constructs and compiles the StateGraph.
    """
    workflow = StateGraph(JarvisState)

    # Add 13 distinct workflow nodes + rejection cleanup
    workflow.add_node("ingest_files", node_ingest_files)
    workflow.add_node("normalize_records", node_normalize_records)
    workflow.add_node("extract_promises", node_extract_promises)
    workflow.add_node("reconcile_payments", node_reconcile_payments)
    workflow.add_node("calculate_settlement_variance", node_calculate_settlement_variance)
    workflow.add_node("build_case", node_build_case)
    workflow.add_node("generate_findings", node_generate_findings)
    workflow.add_node("prepare_action", node_prepare_action)
    workflow.add_node("request_approval", node_request_approval)
    workflow.add_node("wait_for_approval", node_wait_for_approval)
    workflow.add_node("execute_approved_action", node_execute_approved_action)
    workflow.add_node("verify_provider_operation", node_verify_provider_operation)
    workflow.add_node("generate_receipt", node_generate_receipt)
    workflow.add_node("rejection_cleanup", node_rejection_cleanup)

    # Conditional dispatch from START to allow clean resumption without repeated ingestion
    workflow.add_conditional_edges(
        START,
        route_from_start,
        {
            "ingest_files": "ingest_files",
            "execute_approved_action": "execute_approved_action",
            "rejection_cleanup": "rejection_cleanup",
        },
    )

    # Linear workflow sequence for investigation & proposal
    workflow.add_edge("ingest_files", "normalize_records")
    workflow.add_edge("normalize_records", "extract_promises")
    workflow.add_edge("extract_promises", "reconcile_payments")
    workflow.add_edge("reconcile_payments", "calculate_settlement_variance")
    workflow.add_edge("calculate_settlement_variance", "build_case")
    workflow.add_edge("build_case", "generate_findings")
    workflow.add_edge("generate_findings", "prepare_action")
    workflow.add_edge("prepare_action", "request_approval")

    # Conditional routing after request_approval
    workflow.add_conditional_edges(
        "request_approval",
        route_after_request_approval,
        {
            "wait_for_approval": "wait_for_approval",
            "execute_approved_action": "execute_approved_action",
            "rejection_cleanup": "rejection_cleanup",
        },
    )

    # Conditional routing after wait_for_approval (interruption / resumption)
    workflow.add_conditional_edges(
        "wait_for_approval",
        route_after_wait_for_approval,
        {
            "execute_approved_action": "execute_approved_action",
            "rejection_cleanup": "rejection_cleanup",
            "__end__": END,
        },
    )

    # Execution, verification, and receipt generation
    workflow.add_edge("execute_approved_action", "verify_provider_operation")
    workflow.add_edge("verify_provider_operation", "generate_receipt")
    workflow.add_edge("generate_receipt", END)
    workflow.add_edge("rejection_cleanup", END)

    return workflow.compile()


# Singleton compiled graph instance
compiled_graph = create_jarvis_graph()


def run_agent_workflow(
    initial_state: JarvisState,
) -> JarvisState:
    """
    Executes the agent workflow from the beginning up to approval pause or completion.
    """
    run_id = initial_state.get("run_id")
    checkpointer.save_checkpoint(initial_state, "START")

    result = compiled_graph.invoke(initial_state)
    final_state = JarvisState(**result)

    # Persist final checkpoint
    current_node = final_state.get("current_node", "COMPLETED")
    checkpointer.save_checkpoint(final_state, current_node)

    return final_state


def resume_agent_workflow(
    run_id: str,
    decision: str,
    rejection_reason: Optional[str] = None,
) -> Optional[JarvisState]:
    """
    Resumes a paused workflow run after the micro-business owner renders an approval decision.
    """
    state = checkpointer.load_checkpoint(run_id)
    if not state:
        return None

    state["approval_decision"] = decision
    if rejection_reason:
        state["rejection_reason"] = rejection_reason

    # Resume graph execution from wait_for_approval
    result = compiled_graph.invoke(state)
    resumed_state = JarvisState(**result)

    current_node = resumed_state.get("current_node", "COMPLETED")
    checkpointer.save_checkpoint(resumed_state, current_node)

    return resumed_state
