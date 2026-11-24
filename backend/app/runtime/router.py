"""
Jarvis Runtime Model Router & Conditional Graph Edge Dispatcher.

Rules:
- Model routing:
  - Use Gemini 3.5 Flash-Lite for extraction, classification, and drafting.
  - Use Gemini 3.8 Flash only for complex reasoning or code analysis if required.
  - Strictly DO NOT use the LLM for reconciliation, calculations, approvals, or policy enforcement.
- Conditional graph routing:
  - Clean interruption and resumption after human approval.
"""

from typing import Optional
from app.runtime.state import JarvisState


# -----------------------------------------------------------------------------
# 1. Model Routing Engine
# -----------------------------------------------------------------------------
class ModelRouter:
    """
    Enforces strict architectural boundaries on LLM usage.
    """
    FLASH_LITE_MODEL = "gemini-2.5-flash"  # Primary Flash-Lite equivalent in Google GenAI SDK
    FLASH_ADVANCED_MODEL = "gemini-2.5-flash"  # Advanced reasoning tier

    DETERMINISTIC_TASKS = {
        "reconciliation",
        "settlement_variance",
        "calculations",
        "approval_check",
        "policy_enforcement",
        "receipt_generation",
        "hash_verification",
    }

    AI_TASKS = {
        "extraction": FLASH_LITE_MODEL,
        "classification": FLASH_LITE_MODEL,
        "drafting": FLASH_LITE_MODEL,
        "complex_reasoning": FLASH_ADVANCED_MODEL,
        "code_analysis": FLASH_ADVANCED_MODEL,
    }

    @classmethod
    def get_model_for_task(cls, task_type: str) -> Optional[str]:
        """
        Returns model identifier for allowed AI tasks.
        Raises ValueError if caller attempts to route reconciliation or math to an LLM.
        """
        task_clean = task_type.strip().lower()

        if task_clean in cls.DETERMINISTIC_TASKS:
            raise ValueError(
                f"Policy Violation: Task '{task_type}' must be executed strictly via "
                f"deterministic Python. LLM invocation is strictly forbidden for calculations and reconciliation."
            )

        if task_clean in cls.AI_TASKS:
            return cls.AI_TASKS[task_clean]

        # Default to Flash-Lite for unknown conversational tasks
        return cls.FLASH_LITE_MODEL


# -----------------------------------------------------------------------------
# 2. Graph Conditional Routing
# -----------------------------------------------------------------------------
def route_from_start(state: JarvisState) -> str:
    """
    Evaluates where to route when the graph is invoked.
    If resuming with an approval decision, jumps directly to execution or rejection
    without re-running file ingestion and case building.
    """
    decision = state.get("approval_decision")
    if decision == "APPROVED":
        return "execute_approved_action"
    if decision == "REJECTED":
        return "rejection_cleanup"
    return "ingest_files"


def route_after_request_approval(state: JarvisState) -> str:
    """
    Evaluates whether approval is required and routes accordingly.
    """
    decision = state.get("approval_decision")
    requires_approval = state.get("requires_approval", True)

    if requires_approval and not decision:
        return "wait_for_approval"

    if decision == "APPROVED":
        return "execute_approved_action"

    if decision == "REJECTED":
        return "rejection_cleanup"

    return "wait_for_approval"


def route_after_wait_for_approval(state: JarvisState) -> str:
    """
    Conditional edge determining execution path once workflow is resumed.
    """
    decision = state.get("approval_decision")

    if decision == "APPROVED":
        return "execute_approved_action"

    if decision == "REJECTED":
        return "rejection_cleanup"

    # Still waiting for seller approval
    return "__end__"
