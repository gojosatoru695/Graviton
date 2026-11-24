"""
Jarvis Deterministic Commercial Case Builder Service.
Converts verified reconciliation findings, settlement variances, duplicate payments,
and payment shortfalls into structured CommercialCase entities with linked Evidence and Findings.

Rules:
- Never invent facts or assumptions.
- Case status starts in NEEDS_APPROVAL or INVESTIGATING.
- Every case includes full evidence links and deterministic mathematical proofs.
- Decimal strictly for all amounts.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.contracts.enums import ActionType, CaseStatus, EvidenceType, Severity
from app.contracts.models import (
    ActionProposal,
    CommercialCase,
    EvidenceItem,
    Finding,
    OrderRecord,
)
from app.services.duplicate_detector import DuplicateCandidateGroup
from app.services.settlement_variance import SettlementVarianceResult


class CaseBuilder:
    """
    Factory for constructing verifiable CommercialCase entities.
    """

    def __init__(self, correlation_id: str):
        self.correlation_id = correlation_id
        self._case_counter = 1

    def _next_case_number(self) -> str:
        num_str = f"CASE-2024-{self._case_counter:03d}"
        self._case_counter += 1
        return num_str

    def build_settlement_variance_case(
        self,
        variance_result: SettlementVarianceResult,
    ) -> CommercialCase:
        """
        Creates a CommercialCase for an unexplained marketplace settlement residual.
        """
        case_num = self._next_case_number()
        case_id = f"case_settle_{variance_result.settlement_id.lower()}"

        unexplained_str = ", ".join(variance_result.unexplained_deductions) if variance_result.unexplained_deductions else "Unitemized platform penalty"

        explanation = (
            f"Marketplace settlement {variance_result.settlement_id} for {variance_result.marketplace} "
            f"transferred ₹{variance_result.actual_bank_credit}, falling short of the expected net payout of "
            f"₹{variance_result.expected_net_payable} by ₹{variance_result.variance_amount}. "
            f"Unexplained deductions identified: {unexplained_str}."
        )

        return CommercialCase(
            case_id=case_id,
            correlation_id=self.correlation_id,
            case_number=case_num,
            title=f"Marketplace Settlement Residual: {variance_result.marketplace} Shortfall ₹{variance_result.variance_amount}",
            case_type="SETTLEMENT_VARIANCE",
            status=CaseStatus.NEEDS_APPROVAL,
            severity=Severity.HIGH,
            customer_id=None,
            order_id=None,
            discrepancy_amount=variance_result.variance_amount,
            headline=f"Unexplained ₹{variance_result.variance_amount} deduction on {variance_result.marketplace} payout.",
            explanation=explanation,
            evidence_items=variance_result.evidence_items,
            findings=variance_result.findings,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def build_duplicate_payment_case(
        self,
        group: DuplicateCandidateGroup,
    ) -> CommercialCase:
        """
        Creates a CommercialCase for candidate duplicate payments requiring human decision.
        """
        case_num = self._next_case_number()
        case_id = f"case_{group.group_id}"

        target_ref = group.order_number or f"Customer {group.customer_name}"
        headline = f"Potential duplicate payment for {target_ref} (Excess: ₹{group.excess_amount})."

        finding = Finding(
            finding_id=f"find_{group.group_id}",
            correlation_id=self.correlation_id,
            finding_type="DUPLICATE_PAYMENT_CANDIDATE",
            proof_description=(
                f"Customer {group.customer_name} transferred {len(group.candidate_transactions)} times. "
                f"Expected: ₹{group.expected_amount}, Total Received: ₹{group.total_received}, "
                f"Excess Received: ₹{group.excess_amount}."
            ),
            impact_amount=group.excess_amount,
            severity=Severity.MEDIUM,
            evidence_ids=[ev.evidence_id for ev in group.evidence_items],
        )

        return CommercialCase(
            case_id=case_id,
            correlation_id=self.correlation_id,
            case_number=case_num,
            title=f"Duplicate Payment Candidate: {target_ref} (₹{group.excess_amount})",
            case_type="DUPLICATE_PAYMENT_CANDIDATE",
            status=CaseStatus.NEEDS_APPROVAL,
            severity=Severity.MEDIUM,
            customer_id=None,
            order_id=group.order_id,
            discrepancy_amount=group.excess_amount,
            headline=headline,
            explanation=group.explanation,
            evidence_items=group.evidence_items,
            findings=[finding],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def build_partial_payment_case(
        self,
        order: OrderRecord,
        paid_amount: Decimal,
        shortfall_amount: Decimal,
        evidence_items: List[EvidenceItem],
    ) -> CommercialCase:
        """
        Creates a CommercialCase for partial payment / payment pending after delivery.
        """
        case_num = self._next_case_number()
        case_id = f"case_partial_{order.order_number.lower()}"

        headline = f"Payment shortfall of ₹{shortfall_amount} for Order {order.order_number}."
        explanation = (
            f"Order {order.order_number} for customer {order.customer_id} has net payable of ₹{order.net_amount}. "
            f"Verified bank credits total ₹{paid_amount}, leaving an uncollected balance shortfall of ₹{shortfall_amount}."
        )

        finding = Finding(
            finding_id=f"find_shortfall_{order.order_number.lower()}",
            correlation_id=self.correlation_id,
            finding_type="PAYMENT_SHORTFALL",
            proof_description=f"Order Net: ₹{order.net_amount} - Paid: ₹{paid_amount} = Shortfall: ₹{shortfall_amount}.",
            impact_amount=shortfall_amount,
            severity=Severity.HIGH if order.status == "DELIVERED" else Severity.MEDIUM,
            evidence_ids=[ev.evidence_id for ev in evidence_items],
        )

        return CommercialCase(
            case_id=case_id,
            correlation_id=self.correlation_id,
            case_number=case_num,
            title=f"Payment Shortfall: {order.order_number} (Unpaid: ₹{shortfall_amount})",
            case_type="PAYMENT_SHORTFALL",
            status=CaseStatus.NEEDS_APPROVAL,
            severity=Severity.HIGH if order.status == "DELIVERED" else Severity.MEDIUM,
            customer_id=order.customer_id,
            order_id=order.order_id,
            discrepancy_amount=shortfall_amount,
            headline=headline,
            explanation=explanation,
            evidence_items=evidence_items,
            findings=[finding],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def build_ambiguous_match_case(
        self,
        txn_id: str,
        amount: Decimal,
        candidate_orders: List[OrderRecord],
        evidence_items: List[EvidenceItem],
        reason: str,
    ) -> CommercialCase:
        """
        Creates a CommercialCase for ambiguous match requiring human review.
        """
        case_num = self._next_case_number()
        case_id = f"case_ambig_{txn_id.lower()}"

        candidate_nums = ", ".join(o.order_number for o in candidate_orders)
        headline = f"Ambiguous bank credit of ₹{amount} matches multiple orders ({candidate_nums})."
        explanation = (
            f"Bank transaction {txn_id} for ₹{amount} could not be unambiguously resolved. "
            f"Candidate matching orders: {candidate_nums}. "
            f"Reason: {reason}. In accordance with Jarvis safety rules, this case is marked for human review."
        )

        finding = Finding(
            finding_id=f"find_ambig_{txn_id.lower()}",
            correlation_id=self.correlation_id,
            finding_type="AMBIGUOUS_PAYMENT_MATCH",
            proof_description=explanation,
            impact_amount=amount,
            severity=Severity.MEDIUM,
            evidence_ids=[ev.evidence_id for ev in evidence_items],
        )

        return CommercialCase(
            case_id=case_id,
            correlation_id=self.correlation_id,
            case_number=case_num,
            title=f"Ambiguous Match: Bank Credit ₹{amount} (Needs Review)",
            case_type="AMBIGUOUS_PAYMENT_MATCH",
            status=CaseStatus.INVESTIGATING,
            severity=Severity.MEDIUM,
            customer_id=None,
            order_id=None,
            discrepancy_amount=amount,
            headline=headline,
            explanation=explanation,
            evidence_items=evidence_items,
            findings=[finding],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
