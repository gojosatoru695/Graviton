"""
Jarvis Policy Rules Engine.
Defines the 13 explicit policy check functions.

Rules:
1. Verify the required connected account exists before an action.
2. Verify the recipient is valid.
3. Verify the action amount is within configured limits (strictly Decimal).
4. Verify the action has sufficient evidence.
5. Block actions based on prompt-injection attempts.
6. Block direct refunds unless explicitly approved.
7. Block messages that promise refunds, gifts, or discounts not supported by evidence.
8. Require approval for all outbound customer messages.
9. Require approval for payment-link creation.
10. Require approval for complaint replies.
11. Allow Gmail draft creation without approval.
12. Require approval before sending an email.
13. Create an immutable receipt after every approved or rejected action.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

from app.contracts.enums import ActionType
from app.contracts.errors import ErrorCode
from app.policy.safety import inspect_for_prompt_injection


@dataclass
class PolicyCheck:
    """
    Individual rule evaluation outcome.
    """
    rule_number: int
    rule_name: str
    passed: bool
    requires_approval: bool = False
    message: str = ""
    error_code: Optional[str] = None


# -----------------------------------------------------------------------------
# Rule 1: Connected Account Verification
# -----------------------------------------------------------------------------
def rule_1_verify_connected_account(
    action_type: str,
    connected_accounts: Optional[Set[str]] = None,
) -> PolicyCheck:
    """
    Verifies that the required platform integration exists before executing an action.
    """
    accounts = {a.lower() for a in (connected_accounts or set())}

    if action_type in [ActionType.RAZORPAY_PAYMENT_LINK.value, "RAZORPAY_PAYMENT_LINK"]:
        if "razorpay" not in accounts:
            return PolicyCheck(
                rule_number=1,
                rule_name="CONNECTED_ACCOUNT_CHECK",
                passed=False,
                error_code=ErrorCode.MISSING_CONNECTED_ACCOUNT.value,
                message="Missing required connected account: Razorpay credentials not configured.",
            )

    elif action_type in [ActionType.GMAIL_DRAFT.value, ActionType.SEND_EMAIL.value, "GMAIL_DRAFT", "SEND_EMAIL"]:
        if "google" not in accounts and "gmail" not in accounts:
            return PolicyCheck(
                rule_number=1,
                rule_name="CONNECTED_ACCOUNT_CHECK",
                passed=False,
                error_code=ErrorCode.MISSING_CONNECTED_ACCOUNT.value,
                message="Missing required connected account: Google/Gmail integration not connected.",
            )

    return PolicyCheck(
        rule_number=1,
        rule_name="CONNECTED_ACCOUNT_CHECK",
        passed=True,
        message="Required connected account verified.",
    )


# -----------------------------------------------------------------------------
# Rule 2: Recipient Validity Verification
# -----------------------------------------------------------------------------
def rule_2_verify_recipient(
    recipient: Optional[str],
    action_type: str,
) -> PolicyCheck:
    """
    Verifies that target recipient is present, non-dummy, and formatted correctly.
    """
    if not recipient or not str(recipient).strip():
        return PolicyCheck(
            rule_number=2,
            rule_name="RECIPIENT_VALIDATION",
            passed=False,
            error_code=ErrorCode.POLICY_BLOCKED.value,
            message="Recipient is missing or empty.",
        )

    rec_clean = str(recipient).strip().lower()

    # Block obvious dummy / invalid recipients
    if rec_clean in ["dummy", "null", "none", "unknown", "test@test", "fraud@upi"]:
        return PolicyCheck(
            rule_number=2,
            rule_name="RECIPIENT_VALIDATION",
            passed=False,
            error_code=ErrorCode.POLICY_BLOCKED.value,
            message=f"Recipient '{recipient}' is recognized as dummy or blocked address.",
        )

    # For email actions, verify email syntax
    if action_type in [ActionType.SEND_EMAIL.value, ActionType.GMAIL_DRAFT.value, "SEND_EMAIL", "GMAIL_DRAFT"]:
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", rec_clean):
            return PolicyCheck(
                rule_number=2,
                rule_name="RECIPIENT_VALIDATION",
                passed=False,
                error_code=ErrorCode.POLICY_BLOCKED.value,
                message=f"Invalid email address format for recipient: '{recipient}'.",
            )

    return PolicyCheck(
        rule_number=2,
        rule_name="RECIPIENT_VALIDATION",
        passed=True,
        message=f"Recipient '{recipient}' verified.",
    )


# -----------------------------------------------------------------------------
# Rule 3: Amount Limits Verification (Strictly Decimal)
# -----------------------------------------------------------------------------
def rule_3_verify_amount_limits(
    amount: Any,
    min_limit: Decimal = Decimal("1.00"),
    max_limit: Decimal = Decimal("50000.00"),
) -> PolicyCheck:
    """
    Verifies that monetary action amounts are positive Decimals within configured limits.
    """
    if amount is None:
        return PolicyCheck(
            rule_number=3,
            rule_name="AMOUNT_LIMIT_CHECK",
            passed=True,
            message="No monetary amount associated with action.",
        )

    try:
        dec_amt = Decimal(str(amount))
    except Exception:
        return PolicyCheck(
            rule_number=3,
            rule_name="AMOUNT_LIMIT_CHECK",
            passed=False,
            error_code=ErrorCode.POLICY_BLOCKED.value,
            message=f"Invalid monetary format '{amount}'.",
        )

    if dec_amt < min_limit:
        return PolicyCheck(
            rule_number=3,
            rule_name="AMOUNT_LIMIT_CHECK",
            passed=False,
            error_code=ErrorCode.POLICY_BLOCKED.value,
            message=f"Action amount ₹{dec_amt} is below minimum allowed ₹{min_limit}.",
        )

    if dec_amt > max_limit:
        return PolicyCheck(
            rule_number=3,
            rule_name="AMOUNT_LIMIT_CHECK",
            passed=False,
            error_code=ErrorCode.POLICY_BLOCKED.value,
            message=f"Action amount ₹{dec_amt} exceeds maximum allowed single transaction limit ₹{max_limit}.",
        )

    return PolicyCheck(
        rule_number=3,
        rule_name="AMOUNT_LIMIT_CHECK",
        passed=True,
        message=f"Amount ₹{dec_amt} is within allowed limits (₹{min_limit} - ₹{max_limit}).",
    )


# -----------------------------------------------------------------------------
# Rule 4: Sufficient Evidence Verification
# -----------------------------------------------------------------------------
def rule_4_verify_sufficient_evidence(
    evidence_ids: Optional[List[str]],
    min_evidence_count: int = 1,
) -> PolicyCheck:
    """
    Verifies that an action links to at least 1 verified evidence item.
    """
    count = len(evidence_ids) if evidence_ids else 0
    if count < min_evidence_count:
        return PolicyCheck(
            rule_number=4,
            rule_name="SUFFICIENT_EVIDENCE_CHECK",
            passed=False,
            error_code=ErrorCode.POLICY_BLOCKED.value,
            message=f"Insufficient evidence: Action requires at least {min_evidence_count} evidence item, found {count}.",
        )

    return PolicyCheck(
        rule_number=4,
        rule_name="SUFFICIENT_EVIDENCE_CHECK",
        passed=True,
        message=f"Sufficient evidence verified ({count} evidence items attached).",
    )


# -----------------------------------------------------------------------------
# Rule 5: Prompt-Injection Defense Verification
# -----------------------------------------------------------------------------
def rule_5_verify_no_prompt_injection(
    message_text: Optional[str],
) -> PolicyCheck:
    """
    Scans source message text for prompt injection.
    Returns PROMPT_INJECTION_BLOCKED if detected.
    """
    if not message_text:
        return PolicyCheck(
            rule_number=5,
            rule_name="PROMPT_INJECTION_DEFENSE",
            passed=True,
            message="No prompt injection detected.",
        )

    result = inspect_for_prompt_injection(message_text)
    if result.is_injection:
        return PolicyCheck(
            rule_number=5,
            rule_name="PROMPT_INJECTION_DEFENSE",
            passed=False,
            error_code=ErrorCode.PROMPT_INJECTION_BLOCKED.value,
            message=f"Action blocked: Prompt-injection attack detected. Threat patterns: {'; '.join(result.threat_patterns)}",
        )

    return PolicyCheck(
        rule_number=5,
        rule_name="PROMPT_INJECTION_DEFENSE",
        passed=True,
        message="Prompt injection firewall clear.",
    )


# -----------------------------------------------------------------------------
# Rule 6: Direct Refund Block
# -----------------------------------------------------------------------------
def rule_6_verify_direct_refund(
    action_type: str,
    is_explicitly_approved: bool = False,
) -> PolicyCheck:
    """
    Blocks direct refunds unless explicitly approved by the seller.
    """
    is_refund_action = "refund" in action_type.lower()
    if is_refund_action and not is_explicitly_approved:
        return PolicyCheck(
            rule_number=6,
            rule_name="DIRECT_REFUND_BLOCK",
            passed=False,
            requires_approval=True,
            error_code=ErrorCode.APPROVAL_REQUIRED.value,
            message="Direct refund blocked. Explicit seller human approval is mandatory.",
        )

    return PolicyCheck(
        rule_number=6,
        rule_name="DIRECT_REFUND_BLOCK",
        passed=True,
        message="Refund check clear.",
    )


# -----------------------------------------------------------------------------
# Rule 7: Content Evidence Backing (No Hallucinated Promises)
# -----------------------------------------------------------------------------
def rule_7_verify_content_evidence_backing(
    message_body: Optional[str],
    verified_evidence_types: Optional[Set[str]] = None,
) -> PolicyCheck:
    """
    Blocks messages that promise refunds, gifts, or discounts if not supported by evidence.
    """
    if not message_body:
        return PolicyCheck(rule_number=7, rule_name="CONTENT_EVIDENCE_BACKING", passed=True)

    ev_types = {e.lower() for e in (verified_evidence_types or set())}
    lower_body = message_body.lower()

    # If message promises refund, ensure verified return / refund evidence exists
    if any(k in lower_body for k in ["refund", "money back", "transferring your refund"]):
        if "refund" not in ev_types and "return_rto" not in ev_types and "chat_refund" not in ev_types:
            return PolicyCheck(
                rule_number=7,
                rule_name="CONTENT_EVIDENCE_BACKING",
                passed=False,
                error_code=ErrorCode.POLICY_BLOCKED.value,
                message="Blocked message: Promises a refund without verified return evidence.",
            )

    # If message promises a free gift, ensure gift evidence exists
    if any(k in lower_body for k in ["free gift", "complimentary gift", "free scrunchie", "gift"]):
        if "free_gift" not in ev_types and "gift" not in ev_types and "promise" not in ev_types:
            return PolicyCheck(
                rule_number=7,
                rule_name="CONTENT_EVIDENCE_BACKING",
                passed=False,
                error_code=ErrorCode.POLICY_BLOCKED.value,
                message="Blocked message: Promises a free gift not supported by evidence.",
            )

    # If message promises a discount, ensure discount evidence exists
    if any(k in lower_body for k in ["discount", "coupon", "off", "special price"]):
        if "discount" not in ev_types and "coupon" not in ev_types and "promise" not in ev_types:
            return PolicyCheck(
                rule_number=7,
                rule_name="CONTENT_EVIDENCE_BACKING",
                passed=False,
                error_code=ErrorCode.POLICY_BLOCKED.value,
                message="Blocked message: Promises a discount not supported by evidence.",
            )

    return PolicyCheck(
        rule_number=7,
        rule_name="CONTENT_EVIDENCE_BACKING",
        passed=True,
        message="Message content verified against evidence.",
    )


# -----------------------------------------------------------------------------
# Rules 8 to 12: Human Approval Requirement Rules
# -----------------------------------------------------------------------------
def rules_8_to_12_requires_approval(action_type: str) -> PolicyCheck:
    """
    Evaluates Rules 8-12:
    - Rule 8: Require approval for all outbound customer messages.
    - Rule 9: Require approval for payment-link creation.
    - Rule 10: Require approval for complaint replies.
    - Rule 11: Allow Gmail draft creation without approval (internal draft).
    - Rule 12: Require approval before sending an email.
    """
    act_lower = action_type.lower()

    # Rule 11: Gmail draft creation allowed without approval!
    if act_lower in ["gmail_draft", ActionType.GMAIL_DRAFT.value.lower()]:
        return PolicyCheck(
            rule_number=11,
            rule_name="GMAIL_DRAFT_APPROVAL_EXEMPTION",
            passed=True,
            requires_approval=False,
            message="Rule 11: Gmail draft creation is an internal draft; human approval is not required.",
        )

    # Rule 8: Outbound customer messages
    if act_lower in ["send_customer_message", ActionType.SEND_CUSTOMER_MESSAGE.value.lower()]:
        return PolicyCheck(
            rule_number=8,
            rule_name="OUTBOUND_CUSTOMER_MESSAGE_APPROVAL",
            passed=True,
            requires_approval=True,
            message="Rule 8: Outbound customer message requires explicit seller approval.",
        )

    # Rule 9: Payment link creation
    if act_lower in ["razorpay_payment_link", ActionType.RAZORPAY_PAYMENT_LINK.value.lower()]:
        return PolicyCheck(
            rule_number=9,
            rule_name="PAYMENT_LINK_CREATION_APPROVAL",
            passed=True,
            requires_approval=True,
            message="Rule 9: Creating Razorpay payment link requires seller approval.",
        )

    # Rule 10: Complaint replies
    if "complaint" in act_lower:
        return PolicyCheck(
            rule_number=10,
            rule_name="COMPLAINT_REPLY_APPROVAL",
            passed=True,
            requires_approval=True,
            message="Rule 10: Replying to customer complaint requires seller approval.",
        )

    # Rule 12: Sending an email
    if act_lower in ["send_email", ActionType.SEND_EMAIL.value.lower()]:
        return PolicyCheck(
            rule_number=12,
            rule_name="SEND_EMAIL_APPROVAL",
            passed=True,
            requires_approval=True,
            message="Rule 12: Sending an email requires explicit seller approval.",
        )

    # Default: Any other outbound/dispute action requires approval
    return PolicyCheck(
        rule_number=8,
        rule_name="DEFAULT_HUMAN_APPROVAL",
        passed=True,
        requires_approval=True,
        message="Action requires explicit seller approval.",
    )
