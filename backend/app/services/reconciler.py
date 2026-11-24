"""
Jarvis Deterministic Reconciliation Engine.
Executes multi-pass deterministic matching between orders, invoices, and bank transactions.

Strict Rules:
- Strictly Decimal for all currency calculations. Never float.
- Never use the LLM for matching or arithmetic.
- Deterministic, transparent matching rules with evidence generated for every match.
- Ambiguous matches are strictly marked as needs_review (never silently auto-resolved).
- Never silently overwrite a payment status.
"""

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from app.contracts.enums import EvidenceType, PaymentStatus, Severity
from app.contracts.errors import ErrorCode, JarvisContractException
from app.contracts.models import (
    BankTransaction,
    CommercialCase,
    EvidenceItem,
    Finding,
    InvoiceRecord,
    OrderRecord,
    PaymentRecord,
)
from app.services.case_builder import CaseBuilder
from app.services.duplicate_detector import (
    DuplicateCandidateGroup,
    detect_duplicate_payments,
)
from app.services.evidence_builder import (
    evidence_from_bank_txn,
    evidence_from_invoice,
    evidence_from_order,
)


@dataclass
class MatchResult:
    """
    Detailed match record for a reconciled transaction or order.
    """
    matched_order_id: Optional[str]
    matched_invoice_id: Optional[str]
    bank_transaction_id: str
    match_score: Decimal
    match_reason: str
    evidence_references: List[str]
    status: PaymentStatus
    human_readable_explanation: str
    expected_amount: Decimal
    paid_amount: Decimal
    shortfall_amount: Decimal
    is_ambiguous: bool = False
    needs_review: bool = False


@dataclass
class UnmatchedItem:
    """
    Detailed audit explanation for an unmatched bank credit or open order.
    """
    item_id: str
    item_type: str  # "BANK_TRANSACTION" or "ORDER"
    correlation_id: str
    reference_id: str
    amount: Decimal
    what_is_missing: str
    likely_explanations: List[str]
    required_evidence: List[str]
    recommended_next_action: str
    date: Optional[date] = None
    raw_reference: Optional[str] = None


@dataclass
class ReconciliationReport:
    """
    Complete audit report produced by the deterministic reconciliation engine.
    """
    correlation_id: str
    matches: List[MatchResult]
    unmatched_items: List[UnmatchedItem]
    duplicate_groups: List[DuplicateCandidateGroup]
    cases: List[CommercialCase]
    payment_records: List[PaymentRecord]
    metrics: Dict[str, Any]


def calculate_name_similarity(name1: Optional[str], name2: Optional[str]) -> Decimal:
    """
    Deterministic, transparent token-overlap similarity between two customer names.
    Returns Decimal between 0.00 and 1.00.
    """
    if not name1 or not name2:
        return Decimal("0.00")

    clean1 = set(re.findall(r"\w+", name1.lower()))
    clean2 = set(re.findall(r"\w+", name2.lower()))

    # Remove common Indian titles / prefixes
    stop_words = {"mr", "mrs", "ms", "dr", "shree", "shri", "smt", "ji"}
    tokens1 = clean1 - stop_words
    tokens2 = clean2 - stop_words

    if not tokens1 or not tokens2:
        return Decimal("0.00")

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    jaccard = Decimal(len(intersection)) / Decimal(len(union))
    return jaccard.quantize(Decimal("0.01"))


class DeterministicReconciler:
    """
    Engine executing deterministic matching between Orders, Invoices, and Bank Transactions.
    """

    def __init__(
        self,
        orders: List[OrderRecord],
        invoices: List[InvoiceRecord],
        bank_transactions: List[BankTransaction],
        correlation_id: str,
        case_builder: Optional[CaseBuilder] = None,
    ):
        self.orders = orders
        self.invoices = invoices
        self.bank_transactions = bank_transactions
        self.correlation_id = correlation_id
        self.case_builder = case_builder or CaseBuilder(correlation_id)

        # Lookups
        self.order_by_number: Dict[str, OrderRecord] = {o.order_number: o for o in orders}
        self.order_by_id: Dict[str, OrderRecord] = {o.order_id: o for o in orders}
        self.invoice_by_order_number: Dict[str, InvoiceRecord] = {}

        # Pre-match orders to invoices
        self._match_orders_to_invoices()

    def _match_orders_to_invoices(self) -> None:
        """
        Deterministic 1:1 match between invoices and orders.
        Matches by exact order_id or order_number reference.
        """
        for inv in self.invoices:
            matched_ord = None
            for order in self.orders:
                if inv.order_id == order.order_id or order.order_number.lower() in inv.order_id.lower() or order.order_number.lower() in inv.invoice_number.lower():
                    matched_ord = order
                    break

            if matched_ord:
                self.invoice_by_order_number[matched_ord.order_number] = inv

    def reconcile(self) -> ReconciliationReport:
        """
        Runs the full deterministic reconciliation pipeline.
        """
        matches: List[MatchResult] = []
        unmatched_items: List[UnmatchedItem] = []
        cases: List[CommercialCase] = []
        payment_records: List[PaymentRecord] = []

        matched_txn_ids: Set[str] = set()
        matched_order_numbers: Set[str] = set()

        # Accumulated payments per order (for partials)
        order_paid_accumulator: Dict[str, Decimal] = {o.order_number: Decimal("0.00") for o in self.orders}
        order_evidence_map: Dict[str, List[EvidenceItem]] = {o.order_number: [] for o in self.orders}

        # Step 1: Detect duplicate payments upfront
        duplicate_groups = detect_duplicate_payments(
            self.bank_transactions,
            self.orders,
            self.correlation_id,
        )

        duplicate_txn_ids = set()
        for group in duplicate_groups:
            case = self.case_builder.build_duplicate_payment_case(group)
            cases.append(case)
            for t in group.candidate_transactions:
                duplicate_txn_ids.add(t.transaction_id)
                # Mark as duplicate candidate match
                matches.append(
                    MatchResult(
                        matched_order_id=group.order_id,
                        matched_invoice_id=self.invoice_by_order_number.get(group.order_number or "", None).invoice_id if self.invoice_by_order_number.get(group.order_number or "") else None,
                        bank_transaction_id=t.transaction_id,
                        match_score=group.confidence,
                        match_reason="DUPLICATE_PAYMENT_CANDIDATE",
                        evidence_references=[ev.evidence_id for ev in group.evidence_items],
                        status=PaymentStatus.DUPLICATE_CANDIDATE,
                        human_readable_explanation=group.explanation,
                        expected_amount=group.expected_amount,
                        paid_amount=t.amount,
                        shortfall_amount=Decimal("0.00"),
                        is_ambiguous=False,
                        needs_review=True,
                    )
                )

        # Step 2: Refund Matching (Debits)
        debit_txns = [
            t for t in self.bank_transactions
            if "DR" in t.transaction_type.upper() or t.amount < Decimal("0.00") or "REFUND" in t.raw_narration.upper()
        ]

        for deb in debit_txns:
            if deb.transaction_id in duplicate_txn_ids:
                continue

            matched_refund_order = None
            # Check narration for order ref
            for ord_num, order_obj in self.order_by_number.items():
                if ord_num in deb.raw_narration or (order_obj.net_amount == deb.amount and order_obj.status == "CANCELLED"):
                    matched_refund_order = order_obj
                    break

            if matched_refund_order:
                matched_txn_ids.add(deb.transaction_id)
                ev_order = evidence_from_order(matched_refund_order, self.correlation_id)
                ev_deb = evidence_from_bank_txn(deb, self.correlation_id)

                matches.append(
                    MatchResult(
                        matched_order_id=matched_refund_order.order_id,
                        matched_invoice_id=self.invoice_by_order_number.get(matched_refund_order.order_number, None).invoice_id if self.invoice_by_order_number.get(matched_refund_order.order_number) else None,
                        bank_transaction_id=deb.transaction_id,
                        match_score=Decimal("1.00"),
                        match_reason="REFUND_MATCH_CANCELLED_ORDER",
                        evidence_references=[ev_order.evidence_id, ev_deb.evidence_id],
                        status=PaymentStatus.REFUND_MATCH,
                        human_readable_explanation=(
                            f"Verified refund debit of ₹{deb.amount} for cancelled order {matched_refund_order.order_number}. "
                            f"UTR: {deb.utr_reference}."
                        ),
                        expected_amount=matched_refund_order.net_amount,
                        paid_amount=deb.amount,
                        shortfall_amount=Decimal("0.00"),
                    )
                )

        # Step 3: Positive Credits - Pass 1 (Exact Amount + Explicit Order Reference in Narration)
        credit_txns = [
            t for t in self.bank_transactions
            if t.transaction_id not in duplicate_txn_ids and t.transaction_id not in matched_txn_ids and "DR" not in t.transaction_type.upper()
        ]

        for txn in credit_txns:
            matched_ord = None
            for ord_num, order_obj in self.order_by_number.items():
                if ord_num in txn.raw_narration and order_obj.net_amount == txn.amount:
                    matched_ord = order_obj
                    break

            if matched_ord:
                matched_txn_ids.add(txn.transaction_id)
                matched_order_numbers.add(matched_ord.order_number)
                order_paid_accumulator[matched_ord.order_number] += txn.amount

                ev_ord = evidence_from_order(matched_ord, self.correlation_id)
                ev_txn = evidence_from_bank_txn(txn, self.correlation_id)
                ev_list = [ev_ord.evidence_id, ev_txn.evidence_id]

                inv = self.invoice_by_order_number.get(matched_ord.order_number)
                inv_id = inv.invoice_id if inv else None
                if inv:
                    ev_inv = evidence_from_invoice(inv, self.correlation_id)
                    ev_list.append(ev_inv.evidence_id)

                matches.append(
                    MatchResult(
                        matched_order_id=matched_ord.order_id,
                        matched_invoice_id=inv_id,
                        bank_transaction_id=txn.transaction_id,
                        match_score=Decimal("1.00"),
                        match_reason="EXACT_AMOUNT_AND_ORDER_REF_IN_NARRATION",
                        evidence_references=ev_list,
                        status=PaymentStatus.PAID,
                        human_readable_explanation=(
                            f"Exact match: ₹{txn.amount} credited for {matched_ord.order_number} "
                            f"with matching order reference in bank narration (UTR: {txn.utr_reference})."
                        ),
                        expected_amount=matched_ord.net_amount,
                        paid_amount=txn.amount,
                        shortfall_amount=Decimal("0.00"),
                    )
                )

        # Step 4: Partial Payments with Explicit Order Reference
        remaining_credits = [t for t in credit_txns if t.transaction_id not in matched_txn_ids]
        for txn in remaining_credits:
            matched_ord = None
            for ord_num, order_obj in self.order_by_number.items():
                if ord_num in txn.raw_narration and txn.amount < order_obj.net_amount:
                    matched_ord = order_obj
                    break

            if matched_ord:
                matched_txn_ids.add(txn.transaction_id)
                matched_order_numbers.add(matched_ord.order_number)
                order_paid_accumulator[matched_ord.order_number] += txn.amount

                shortfall = matched_ord.net_amount - order_paid_accumulator[matched_ord.order_number]
                ev_ord = evidence_from_order(matched_ord, self.correlation_id)
                ev_txn = evidence_from_bank_txn(txn, self.correlation_id)
                order_evidence_map[matched_ord.order_number].extend([ev_ord, ev_txn])

                matches.append(
                    MatchResult(
                        matched_order_id=matched_ord.order_id,
                        matched_invoice_id=self.invoice_by_order_number.get(matched_ord.order_number, None).invoice_id if self.invoice_by_order_number.get(matched_ord.order_number) else None,
                        bank_transaction_id=txn.transaction_id,
                        match_score=Decimal("0.95"),
                        match_reason="PARTIAL_PAYMENT_ORDER_REF_MATCH",
                        evidence_references=[ev_ord.evidence_id, ev_txn.evidence_id],
                        status=PaymentStatus.PARTIALLY_PAID,
                        human_readable_explanation=(
                            f"Partial payment received: ₹{txn.amount} for Order {matched_ord.order_number} "
                            f"(Net: ₹{matched_ord.net_amount}). Outstanding shortfall: ₹{shortfall}."
                        ),
                        expected_amount=matched_ord.net_amount,
                        paid_amount=txn.amount,
                        shortfall_amount=shortfall,
                    )
                )

                # Create partial payment case
                case = self.case_builder.build_partial_payment_case(
                    order=matched_ord,
                    paid_amount=order_paid_accumulator[matched_ord.order_number],
                    shortfall_amount=shortfall,
                    evidence_items=[ev_ord, ev_txn],
                )
                cases.append(case)

        # Step 5: Exact Amount + Customer Name Similarity + Date Window
        remaining_credits = [t for t in credit_txns if t.transaction_id not in matched_txn_ids]
        for txn in remaining_credits:
            candidates: List[OrderRecord] = []
            for ord_num, order_obj in self.order_by_number.items():
                if ord_num in matched_order_numbers:
                    continue

                # Check amount
                if order_obj.net_amount != txn.amount:
                    continue

                # Check date window (+/- 5 days)
                day_delta = abs((txn.transaction_date - order_obj.order_date).days)
                if day_delta > 5:
                    continue

                # Check name similarity
                sim = calculate_name_similarity(order_obj.customer_id, txn.sender_name)
                if sim >= Decimal("0.75"):
                    candidates.append(order_obj)

            if len(candidates) == 1:
                # Single unambiguous match
                matched_ord = candidates[0]
                matched_txn_ids.add(txn.transaction_id)
                matched_order_numbers.add(matched_ord.order_number)
                order_paid_accumulator[matched_ord.order_number] += txn.amount

                ev_ord = evidence_from_order(matched_ord, self.correlation_id)
                ev_txn = evidence_from_bank_txn(txn, self.correlation_id, confidence=Decimal("0.85"))

                matches.append(
                    MatchResult(
                        matched_order_id=matched_ord.order_id,
                        matched_invoice_id=self.invoice_by_order_number.get(matched_ord.order_number, None).invoice_id if self.invoice_by_order_number.get(matched_ord.order_number) else None,
                        bank_transaction_id=txn.transaction_id,
                        match_score=Decimal("0.85"),
                        match_reason="EXACT_AMOUNT_AND_NAME_SIMILARITY",
                        evidence_references=[ev_ord.evidence_id, ev_txn.evidence_id],
                        status=PaymentStatus.PAID,
                        human_readable_explanation=(
                            f"Matched ₹{txn.amount} to Order {matched_ord.order_number} via exact amount "
                            f"and customer name similarity ({matched_ord.customer_id} ~ {txn.sender_name})."
                        ),
                        expected_amount=matched_ord.net_amount,
                        paid_amount=txn.amount,
                        shortfall_amount=Decimal("0.00"),
                    )
                )

            elif len(candidates) > 1:
                # Ambiguous match - mark for review!
                matched_txn_ids.add(txn.transaction_id)
                ev_items = [evidence_from_bank_txn(txn, self.correlation_id, confidence=Decimal("0.50"))]
                for c in candidates:
                    ev_items.append(evidence_from_order(c, self.correlation_id))

                matches.append(
                    MatchResult(
                        matched_order_id=None,
                        matched_invoice_id=None,
                        bank_transaction_id=txn.transaction_id,
                        match_score=Decimal("0.50"),
                        match_reason="AMBIGUOUS_PAYMENT_MATCH",
                        evidence_references=[ev.evidence_id for ev in ev_items],
                        status=PaymentStatus.UNMATCHED_CREDIT,
                        human_readable_explanation=(
                            f"Ambiguous credit: ₹{txn.amount} from '{txn.sender_name}' matches {len(candidates)} "
                            f"orders ({', '.join(c.order_number for c in candidates)}). Requires human review."
                        ),
                        expected_amount=txn.amount,
                        paid_amount=txn.amount,
                        shortfall_amount=Decimal("0.00"),
                        is_ambiguous=True,
                        needs_review=True,
                    )
                )

                case = self.case_builder.build_ambiguous_match_case(
                    txn_id=txn.transaction_id,
                    amount=txn.amount,
                    candidate_orders=candidates,
                    evidence_items=ev_items,
                    reason=f"Exact amount ₹{txn.amount} matches multiple orders within 5-day window",
                )
                cases.append(case)

        # Step 6: Identify Unmatched Bank Credits
        unmatched_credits = [t for t in self.bank_transactions if t.transaction_id not in matched_txn_ids and t.transaction_id not in duplicate_txn_ids]
        for txn in unmatched_credits:
            unmatched_items.append(
                UnmatchedItem(
                    item_id=f"unmatched_txn_{txn.transaction_id}",
                    item_type="BANK_TRANSACTION",
                    correlation_id=self.correlation_id,
                    reference_id=txn.transaction_id,
                    amount=txn.amount,
                    date=txn.transaction_date,
                    raw_reference=txn.utr_reference,
                    what_is_missing="Linked order number or matching order net balance in order book.",
                    likely_explanations=[
                        "Customer made direct UPI payment without quoting order ID.",
                        "Order was placed offline or in-store via QR transfer.",
                        "Typo in order number in UPI transfer narration.",
                        "Marketplace or bulk settlement deposit.",
                    ],
                    required_evidence=[
                        "Customer WhatsApp conversation or DM confirming transaction UTR.",
                        "Seller physical sales ledger entry.",
                    ],
                    recommended_next_action="Review narration and link manually to open customer order or mark as direct income.",
                )
            )

        # Step 7: Identify Unmatched Orders (Orders placed with no matching payment)
        unmatched_orders = [o for o in self.orders if o.order_number not in matched_order_numbers and o.channel != "Meesho"]
        for ord_obj in unmatched_orders:
            unmatched_items.append(
                UnmatchedItem(
                    item_id=f"unmatched_ord_{ord_obj.order_number}",
                    item_type="ORDER",
                    correlation_id=self.correlation_id,
                    reference_id=ord_obj.order_number,
                    amount=ord_obj.net_amount,
                    date=ord_obj.order_date,
                    raw_reference=ord_obj.order_number,
                    what_is_missing=f"Bank credit of ₹{ord_obj.net_amount} matching order {ord_obj.order_number}.",
                    likely_explanations=[
                        "Customer has not yet transferred payment (unpaid / pending COD).",
                        "Payment made under different name or account not yet reconciled.",
                        "Payment failed or pending at gateway.",
                    ],
                    required_evidence=[
                        "Bank statement covering order date + 7 days.",
                        "Razorpay payment gateway dashboard screenshot or webhook log.",
                    ],
                    recommended_next_action="Send polite payment reminder with Razorpay payment link to customer.",
                )
            )

        # Step 8: Build PaymentRecords
        for m in matches:
            pr = PaymentRecord(
                payment_id=f"pay_{m.bank_transaction_id.lower()}",
                correlation_id=self.correlation_id,
                order_id=m.matched_order_id,
                bank_transaction_id=m.bank_transaction_id,
                expected_amount=m.expected_amount,
                paid_amount=m.paid_amount,
                shortfall_amount=m.shortfall_amount,
                status=m.status,
            )
            payment_records.append(pr)

        metrics = {
            "total_orders": len(self.orders),
            "total_invoices": len(self.invoices),
            "total_bank_transactions": len(self.bank_transactions),
            "total_matches": len(matches),
            "exact_matches": sum(1 for m in matches if m.status == PaymentStatus.PAID and m.match_score == Decimal("1.00")),
            "partial_matches": sum(1 for m in matches if m.status == PaymentStatus.PARTIALLY_PAID),
            "duplicate_candidates": len(duplicate_groups),
            "refund_matches": sum(1 for m in matches if m.status == PaymentStatus.REFUND_MATCH),
            "ambiguous_matches": sum(1 for m in matches if m.is_ambiguous),
            "unmatched_credits": len(unmatched_credits),
            "unmatched_orders": len(unmatched_orders),
            "cases_created": len(cases),
        }

        return ReconciliationReport(
            correlation_id=self.correlation_id,
            matches=matches,
            unmatched_items=unmatched_items,
            duplicate_groups=duplicate_groups,
            cases=cases,
            payment_records=payment_records,
            metrics=metrics,
        )
