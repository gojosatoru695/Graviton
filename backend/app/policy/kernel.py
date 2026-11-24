"""
Jarvis Policy Kernel.
Central evaluation coordinator enforcing the 13 Jarvis commercial safety rules.

Rules:
- Strictly readable, testable, deterministic Python (zero OPA).
- Evaluates connected accounts, recipients, amount limits, evidence, prompt injection, and approvals.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

from app.contracts.enums import ActionType
from app.contracts.errors import ErrorCode
from app.policy.rules import (
    PolicyCheck,
    rule_1_verify_connected_account,
    rule_2_verify_recipient,
    rule_3_verify_amount_limits,
    rule_4_verify_sufficient_evidence,
    rule_5_verify_no_prompt_injection,
    rule_6_verify_direct_refund,
    rule_7_verify_content_evidence_backing,
    rules_8_to_12_requires_approval,
)


@dataclass
class PolicyEvaluationResult:
    """
    Complete policy evaluation output for an action proposal.
    """
    is_allowed: bool
    requires_human_approval: bool
    error_code: Optional[str] = None
    violations: List[str] = field(default_factory=list)
    policy_checks: List[Dict[str, Any]] = field(default_factory=list)
    sanitized_payload: Optional[Dict[str, Any]] = None


class PolicyKernel:
    """
    Evaluation engine checking actions against all 13 safety rules.
    """

    def __init__(
        self,
        default_connected_accounts: Optional[Set[str]] = None,
        min_amount: Decimal = Decimal("1.00"),
        max_amount: Decimal = Decimal("50000.00"),
    ):
        # Default mock connected accounts for demo sandbox if none specified
        self.connected_accounts = {
            a.lower() for a in (default_connected_accounts or {"razorpay", "google", "gmail", "meesho"})
        }
        self.min_amount = min_amount
        self.max_amount = max_amount

    def evaluate_action(
        self,
        action_type: str,
        target_recipient: Optional[str],
        amount: Optional[Any] = None,
        evidence_ids: Optional[List[str]] = None,
        source_message_text: Optional[str] = None,
        message_body: Optional[str] = None,
        verified_evidence_types: Optional[Set[str]] = None,
        is_explicitly_approved: bool = False,
        connected_accounts: Optional[Set[str]] = None,
    ) -> PolicyEvaluationResult:
        """
        Runs comprehensive evaluation against the 13 policy rules.
        """
        active_accounts = (
            {a.lower() for a in connected_accounts}
            if connected_accounts is not None
            else self.connected_accounts
        )

        checks: List[PolicyCheck] = []
        violations: List[str] = []
        error_code: Optional[str] = None

        # Rule 1: Connected Account
        c1 = rule_1_verify_connected_account(action_type, active_accounts)
        checks.append(c1)
        if not c1.passed:
            violations.append(c1.message)
            error_code = error_code or c1.error_code

        # Rule 2: Recipient Validity
        c2 = rule_2_verify_recipient(target_recipient, action_type)
        checks.append(c2)
        if not c2.passed:
            violations.append(c2.message)
            error_code = error_code or c2.error_code

        # Rule 3: Amount Limits (Decimal)
        c3 = rule_3_verify_amount_limits(amount, self.min_amount, self.max_amount)
        checks.append(c3)
        if not c3.passed:
            violations.append(c3.message)
            error_code = error_code or c3.error_code

        # Rule 4: Sufficient Evidence
        c4 = rule_4_verify_sufficient_evidence(evidence_ids, min_evidence_count=1)
        checks.append(c4)
        if not c4.passed:
            violations.append(c4.message)
            error_code = error_code or c4.error_code

        # Rule 5: Prompt-Injection Defense
        c5 = rule_5_verify_no_prompt_injection(source_message_text)
        checks.append(c5)
        if not c5.passed:
            violations.append(c5.message)
            error_code = error_code or c5.error_code

        # Rule 6: Direct Refund Block
        c6 = rule_6_verify_direct_refund(action_type, is_explicitly_approved)
        checks.append(c6)
        if not c6.passed:
            violations.append(c6.message)
            error_code = error_code or c6.error_code

        # Rule 7: Content Evidence Backing
        c7 = rule_7_verify_content_evidence_backing(message_body, verified_evidence_types)
        checks.append(c7)
        if not c7.passed:
            violations.append(c7.message)
            error_code = error_code or c7.error_code

        # Rules 8-12: Human Approval Requirement
        approval_check = rules_8_to_12_requires_approval(action_type)
        checks.append(approval_check)
        requires_human_approval = approval_check.requires_approval

        is_allowed = len(violations) == 0

        # Prepare formatted checks dictionary for receipts
        checks_data = [
            {
                "rule_number": c.rule_number,
                "rule_name": c.rule_name,
                "passed": c.passed,
                "requires_approval": c.requires_approval,
                "message": c.message,
                "error_code": c.error_code,
            }
            for c in checks
        ]

        return PolicyEvaluationResult(
            is_allowed=is_allowed,
            requires_human_approval=requires_human_approval,
            error_code=error_code,
            violations=violations,
            policy_checks=checks_data,
        )
