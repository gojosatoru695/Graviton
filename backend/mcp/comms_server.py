"""
Jarvis Communication FastMCP Server.

Exposes controlled, policy-cleared tools for preparing and sending customer communications
via Email, Gmail drafts, and WhatsApp.

Rules:
- Validates inputs using strict Pydantic models.
- Returns structured, deterministic dictionaries.
- Never exposes raw secrets or executes unapproved outbound actions.
- Enforces Policy Rules 5 (Prompt-Injection Defense), 7 (Content Evidence Backing),
  8 (Outbound Message Approval), 11 (Gmail Draft Exemption), and 12 (Email Approval).
- Masks sensitive customer PII in logs and representations.
- Zero raw secrets exposed.
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from fastmcp import FastMCP

from app.database import SessionLocal
from app.models.cases import Case, CaseEvidence, PendingAction
from app.contracts.enums import ActionType
from app.contracts.errors import ErrorCode
from app.policy.kernel import PolicyKernel
from app.policy.safety import inspect_for_prompt_injection
from app.policy.rules import rule_7_verify_content_evidence_backing
from app.services.gmail_service import GmailDraftService

logger = logging.getLogger("jarvis.mcp.comms")
logging.basicConfig(level=logging.INFO)

mcp = FastMCP("Jarvis-Comms-MCP")
policy_kernel = PolicyKernel()


# ---------------------------------------------------------------------------
# Helpers & Security Sanitization
# ---------------------------------------------------------------------------
def mask_pii(text: Optional[str]) -> str:
    """Masks phone numbers and emails in log records and tool outputs."""
    if not text:
        return ""
    # Mask phone numbers
    s = re.sub(r"(\+?\d{2,4})?\d{6}(\d{2})", r"\1******\2", str(text))
    # Mask email
    s = re.sub(r"([^@\s]{2})[^@\s]+(@[^@\s]+)", r"\1***\2", s)
    return s


def log_tool_call(tool_name: str, **kwargs: Any) -> None:
    """Audit logs tool invocations without leaking sensitive values."""
    sanitized = {
        k: mask_pii(str(v))
        if any(x in k.lower() for x in ["phone", "email", "recipient", "contact"])
        else v
        for k, v in kwargs.items()
    }
    logger.info(f"[MCP:Comms] {tool_name} invoked with args: {sanitized}")


# ---------------------------------------------------------------------------
# Input Contracts
# ---------------------------------------------------------------------------
class DraftEmailInput(BaseModel):
    recipient: str = Field(..., description="Target email address")
    subject: str = Field(..., min_length=1, max_length=200, description="Email subject line")
    body: str = Field(..., min_length=1, description="Email body content")
    case_id: Optional[str] = Field(None, description="Optional associated case ID")

    @field_validator("recipient")
    @classmethod
    def validate_recipient(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean in ["dummy", "null", "none", "unknown", "test@test"]:
            raise ValueError(f"Blocked recipient: '{v}' is invalid or dummy address.")
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError(f"Invalid email format: '{v}'")
        return v.strip()


class CreateGmailDraftInput(BaseModel):
    recipient: str = Field(..., description="Target recipient email address")
    subject: str = Field(..., min_length=1, max_length=200, description="Draft subject line")
    body: str = Field(..., min_length=1, description="Draft body content")
    case_id: Optional[str] = Field(None, description="Optional associated case ID")

    @field_validator("recipient")
    @classmethod
    def validate_recipient(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean in ["dummy", "null", "none", "unknown", "test@test"]:
            raise ValueError(f"Blocked recipient: '{v}' is invalid or dummy address.")
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError(f"Invalid email format: '{v}'")
        return v.strip()


class SendApprovedEmailInput(BaseModel):
    action_id: str = Field(..., min_length=1, description="ID of the approved PendingAction")
    recipient: str = Field(..., description="Target email address")
    subject: str = Field(..., min_length=1, max_length=200, description="Email subject")
    body: str = Field(..., min_length=1, description="Email body")
    case_id: str = Field(..., min_length=1, description="Associated Case ID")

    @field_validator("recipient")
    @classmethod
    def validate_recipient(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError(f"Invalid email format: '{v}'")
        return v.strip()


class DraftWhatsappMessageInput(BaseModel):
    recipient_phone: str = Field(..., min_length=8, max_length=25, description="Customer phone number (e.g., +919876543210)")
    customer_name: str = Field(..., min_length=1, max_length=100, description="Customer display name")
    message_body: str = Field(..., min_length=1, description="WhatsApp message body content")
    case_id: Optional[str] = Field(None, description="Optional associated case ID")

    @field_validator("recipient_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean = re.sub(r"[\s\-\(\)]", "", v)
        if not re.match(r"^\+?\d{8,15}$", clean):
            raise ValueError(f"Invalid phone number format: '{v}'")
        return clean


class LogCommunicationResultInput(BaseModel):
    communication_id: str = Field(..., min_length=1, description="Identifier for communication attempt")
    channel: str = Field(..., description="Communication channel: EMAIL, GMAIL, WHATSAPP, or SMS")
    status: str = Field(..., description="Status: DRAFTED, SENT, DELIVERED, FAILED, or BLOCKED")
    details: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary")

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        allowed = {"EMAIL", "GMAIL", "WHATSAPP", "SMS"}
        if v.upper() not in allowed:
            raise ValueError(f"Invalid channel '{v}'. Must be one of {allowed}")
        return v.upper()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"DRAFTED", "SENT", "DELIVERED", "FAILED", "BLOCKED"}
        if v.upper() not in allowed:
            raise ValueError(f"Invalid status '{v}'. Must be one of {allowed}")
        return v.upper()


# ---------------------------------------------------------------------------
# MCP Tools (Exact Required 5 Tools)
# ---------------------------------------------------------------------------
@mcp.tool()
def draft_email(
    recipient: str,
    subject: str,
    body: str,
    case_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Drafts an email message with prompt-injection defense and policy clearance.
    Does NOT send outbound email. Requires approval before sending.
    """
    log_tool_call("draft_email", recipient=recipient, subject=subject, case_id=case_id)
    validated = DraftEmailInput(recipient=recipient, subject=subject, body=body, case_id=case_id)

    # 1. Prompt-Injection Defense (Rule 5)
    body_check = inspect_for_prompt_injection(validated.body, channel="Email", speaker="UNTRUSTED")
    if body_check.is_injection:
        return {
            "success": False,
            "error_code": ErrorCode.PROMPT_INJECTION_BLOCKED.value,
            "message": "Prompt-injection detected in email body content.",
            "threat_patterns": body_check.threat_patterns,
            "quarantine_evidence": body_check.original_message_evidence,
        }

    subject_check = inspect_for_prompt_injection(validated.subject, channel="Email", speaker="UNTRUSTED")
    if subject_check.is_injection:
        return {
            "success": False,
            "error_code": ErrorCode.PROMPT_INJECTION_BLOCKED.value,
            "message": "Prompt-injection detected in email subject line.",
            "threat_patterns": subject_check.threat_patterns,
            "quarantine_evidence": subject_check.original_message_evidence,
        }

    # 2. Content Evidence Backing (Rule 7)
    db = SessionLocal()
    evidence_types = set()
    try:
        if validated.case_id:
            ev_items = db.query(CaseEvidence).filter(CaseEvidence.case_id == validated.case_id).all()
            evidence_types = {e.evidence_type.lower() for e in ev_items}
    finally:
        db.close()

    r7 = rule_7_verify_content_evidence_backing(validated.body, evidence_types)
    if not r7.passed:
        return {
            "success": False,
            "error_code": r7.error_code or ErrorCode.POLICY_BLOCKED.value,
            "message": r7.message,
        }

    draft_id = f"draft_eml_{uuid.uuid4().hex[:8]}"
    return {
        "success": True,
        "draft_id": draft_id,
        "recipient": mask_pii(validated.recipient),
        "raw_recipient": validated.recipient,
        "subject": validated.subject,
        "body": validated.body,
        "case_id": validated.case_id,
        "requires_approval": True,  # Per Rule 8 & Rule 12: Sending requires human approval
        "status": "DRAFT_PREPARED",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def create_gmail_draft(
    recipient: str,
    subject: str,
    body: str,
    case_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates an internal Gmail draft without requiring human approval (Rule 11).
    Never sends live outbound email; strictly saves simulated/sandbox draft.
    """
    log_tool_call("create_gmail_draft", recipient=recipient, subject=subject, case_id=case_id)
    validated = CreateGmailDraftInput(recipient=recipient, subject=subject, body=body, case_id=case_id)

    # 1. Prompt-Injection Defense (Rule 5)
    body_check = inspect_for_prompt_injection(validated.body, channel="Gmail", speaker="UNTRUSTED")
    if body_check.is_injection:
        return {
            "success": False,
            "error_code": ErrorCode.PROMPT_INJECTION_BLOCKED.value,
            "message": "Prompt-injection detected in draft body.",
            "threat_patterns": body_check.threat_patterns,
            "quarantine_evidence": body_check.original_message_evidence,
        }

    # 2. Rule 11 allows Gmail draft creation without approval
    draft = GmailDraftService.create_draft(
        recipient=validated.recipient,
        subject=validated.subject,
        body=validated.body,
    )

    # 3. If case_id provided, stage in database as PendingAction (or record audit item)
    action_id = None
    if validated.case_id:
        db = SessionLocal()
        try:
            case = db.query(Case).filter(Case.id == validated.case_id).first()
            if case:
                action_id = f"act_{uuid.uuid4().hex[:8]}"
                pending_act = PendingAction(
                    id=action_id,
                    case_id=validated.case_id,
                    action_type=ActionType.GMAIL_DRAFT.value,
                    target_recipient=validated.recipient,
                    action_summary=f"Gmail draft saved: '{validated.subject}'",
                    payload=draft,
                    status="PENDING",
                )
                db.add(pending_act)
                db.commit()
        finally:
            db.close()

    return {
        "success": True,
        "draft_id": draft["draft_id"],
        "message_id": draft["message_id"],
        "action_id": action_id,
        "recipient": mask_pii(validated.recipient),
        "raw_recipient": validated.recipient,
        "subject": validated.subject,
        "status": "DRAFT_SAVED",
        "approval_required": False,  # Rule 11 explicit exemption
        "simulated": True,
        "outbound_sent": False,
        "case_id": validated.case_id,
    }


@mcp.tool()
def send_approved_email(
    action_id: str,
    recipient: str,
    subject: str,
    body: str,
    case_id: str,
) -> Dict[str, Any]:
    """
    Sends an outbound email only AFTER verifying explicit human approval in the database.
    STRICT POLICY CLEARANCE (Rules 8 & 12):
    Never allows an LLM to execute an action without explicit human approval.
    """
    log_tool_call("send_approved_email", action_id=action_id, recipient=recipient, case_id=case_id)
    validated = SendApprovedEmailInput(
        action_id=action_id,
        recipient=recipient,
        subject=subject,
        body=body,
        case_id=case_id,
    )

    db = SessionLocal()
    try:
        action = db.query(PendingAction).filter(PendingAction.id == validated.action_id).first()
        if not action:
            return {
                "success": False,
                "error_code": ErrorCode.APPROVAL_REQUIRED.value,
                "policy_cleared": False,
                "message": f"Action '{validated.action_id}' not found. Cannot dispatch unapproved email.",
            }

        # Policy clearance verification: Must be APPROVED
        if action.status != "APPROVED":
            return {
                "success": False,
                "error_code": ErrorCode.APPROVAL_REQUIRED.value,
                "policy_cleared": False,
                "current_status": action.status,
                "message": f"Action '{validated.action_id}' has status '{action.status}'. Explicit human approval is required before outbound email dispatch.",
            }

        if action.case_id != validated.case_id:
            return {
                "success": False,
                "error_code": ErrorCode.POLICY_BLOCKED.value,
                "policy_cleared": False,
                "message": f"Action case mismatch: action is linked to '{action.case_id}', not '{validated.case_id}'.",
            }

        # Action is policy-cleared and human-approved: execute dispatch
        action.status = "EXECUTED"
        db.commit()

        sent_msg_id = f"sent_msg_{uuid.uuid4().hex[:12]}"
        return {
            "success": True,
            "policy_cleared": True,
            "action_id": action.id,
            "message_id": sent_msg_id,
            "recipient": mask_pii(validated.recipient),
            "raw_recipient": validated.recipient,
            "subject": validated.subject,
            "status": "SENT",
            "simulated": True,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        db.close()


@mcp.tool()
def draft_whatsapp_message(
    recipient_phone: str,
    customer_name: str,
    message_body: str,
    case_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Drafts a WhatsApp customer communication with prompt-injection inspection and evidence check.
    Outbound delivery requires human approval per Policy Rule 8.
    """
    log_tool_call("draft_whatsapp_message", recipient_phone=recipient_phone, customer_name=customer_name, case_id=case_id)
    validated = DraftWhatsappMessageInput(
        recipient_phone=recipient_phone,
        customer_name=customer_name,
        message_body=message_body,
        case_id=case_id,
    )

    # 1. Prompt-Injection Defense (Rule 5)
    safety_check = inspect_for_prompt_injection(validated.message_body, channel="WhatsApp", speaker="UNTRUSTED")
    if safety_check.is_injection:
        return {
            "success": False,
            "error_code": ErrorCode.PROMPT_INJECTION_BLOCKED.value,
            "message": "Prompt-injection detected in WhatsApp message content.",
            "threat_patterns": safety_check.threat_patterns,
            "quarantine_evidence": safety_check.original_message_evidence,
        }

    # 2. Content Evidence Backing (Rule 7)
    db = SessionLocal()
    evidence_types = set()
    try:
        if validated.case_id:
            ev_items = db.query(CaseEvidence).filter(CaseEvidence.case_id == validated.case_id).all()
            evidence_types = {e.evidence_type.lower() for e in ev_items}
    finally:
        db.close()

    r7 = rule_7_verify_content_evidence_backing(validated.message_body, evidence_types)
    if not r7.passed:
        return {
            "success": False,
            "error_code": r7.error_code or ErrorCode.POLICY_BLOCKED.value,
            "message": r7.message,
        }

    draft_id = f"wa_draft_{uuid.uuid4().hex[:8]}"
    return {
        "success": True,
        "draft_id": draft_id,
        "recipient_phone": mask_pii(validated.recipient_phone),
        "raw_recipient_phone": validated.recipient_phone,
        "customer_name": validated.customer_name,
        "message_body": validated.message_body,
        "requires_approval": True,  # Per Rule 8: Outbound messages require human approval
        "approval_channel": "HITL_PORTAL",
        "status": "DRAFT_PREPARED",
        "case_id": validated.case_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def log_communication_result(
    communication_id: str,
    channel: str,
    status: str,
    details: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Securely audit-logs communication outcomes without leaking sensitive customer PII or raw tokens.
    """
    log_tool_call("log_communication_result", communication_id=communication_id, channel=channel, status=status)
    validated = LogCommunicationResultInput(
        communication_id=communication_id,
        channel=channel,
        status=status,
        details=details,
    )

    # Sanitize details
    sanitized_details = {}
    for k, v in validated.details.items():
        if any(x in k.lower() for x in ["phone", "email", "recipient", "contact", "secret", "token", "auth"]):
            sanitized_details[k] = mask_pii(str(v))
        else:
            sanitized_details[k] = v

    logger.info(
        f"[MCP:Comms:Audit] ID={validated.communication_id} Channel={validated.channel} "
        f"Status={validated.status} Details={sanitized_details}"
    )

    return {
        "logged": True,
        "communication_id": validated.communication_id,
        "channel": validated.channel,
        "status": validated.status,
        "masked_details": sanitized_details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
