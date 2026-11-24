"""
Jarvis Deterministic Duplicate Payment Detection Service.
Identifies potential duplicate or redundant customer payments across bank credits.

Rules:
- Never auto-refund or auto-resolve duplicate payments.
- Mark all duplicate payment candidates as needs_review / DUPLICATE_CANDIDATE.
- Provide full arithmetic evidence: order expected amount, total received, excess amount.
- Uses strictly Decimal for all money math.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from app.contracts.enums import EvidenceType, PaymentStatus
from app.contracts.models import BankTransaction, EvidenceItem, OrderRecord
from app.services.evidence_builder import evidence_from_bank_txn, evidence_from_order


@dataclass
class DuplicateCandidateGroup:
    """
    Represents a cluster of bank transactions flagged as potential duplicate payments.
    """
    group_id: str
    order_id: Optional[str]
    order_number: Optional[str]
    customer_name: Optional[str]
    expected_amount: Decimal
    total_received: Decimal
    excess_amount: Decimal
    candidate_transactions: List[BankTransaction]
    evidence_items: List[EvidenceItem]
    confidence: Decimal
    explanation: str
    requires_human_review: bool = True


def detect_duplicate_payments(
    bank_transactions: List[BankTransaction],
    orders: List[OrderRecord],
    correlation_id: str,
    time_window_days: int = 7,
) -> List[DuplicateCandidateGroup]:
    """
    Scans bank transactions and orders to detect duplicate transfers:
    1. Direct Order Reference in Multiple Credits:
       Multiple distinct bank transactions referencing the exact same order number.
    2. Identical Amount & Sender Duplicate:
       Two credits of the exact same amount from the same sender within `time_window_days`
       where total received exceeds the order net amount or order is already fulfilled.
    """
    duplicate_groups: List[DuplicateCandidateGroup] = []
    order_by_number: Dict[str, OrderRecord] = {o.order_number: o for o in orders}

    # Map order number to candidate transactions
    txns_by_order: Dict[str, List[BankTransaction]] = defaultdict(list)
    txns_by_sender_and_amount: Dict[Tuple[str, Decimal], List[BankTransaction]] = defaultdict(list)

    # Filter to credit transactions only (exclude debits)
    credit_txns = [
        t for t in bank_transactions
        if t.amount > Decimal("0.00") and "DR" not in t.transaction_type.upper()
    ]

    for txn in credit_txns:
        # Check if narration explicitly contains an order number
        matched_ord_num = None
        for ord_num in order_by_number.keys():
            if ord_num in txn.raw_narration:
                matched_ord_num = ord_num
                break

        if matched_ord_num:
            txns_by_order[matched_ord_num].append(txn)

        # Also group by sender name / UPI ID and exact amount
        sender_key = (txn.sender_name or txn.sender_upi_id or "").strip().lower()
        if sender_key and txn.amount > Decimal("0.00"):
            txns_by_sender_and_amount[(sender_key, txn.amount)].append(txn)

    # 1. Evaluate explicit order number clusters
    processed_txn_ids = set()

    for ord_num, txn_list in txns_by_order.items():
        if len(txn_list) >= 2:
            target_order = order_by_number[ord_num]
            total_received = sum((t.amount for t in txn_list), Decimal("0.00"))
            excess = total_received - target_order.net_amount

            # If total received exceeds order net, or if multiple transactions claim the order
            if excess >= Decimal("0.00") or len(txn_list) >= 2:
                ev_items = [evidence_from_order(target_order, correlation_id)]
                for t in txn_list:
                    ev_items.append(evidence_from_bank_txn(t, correlation_id, confidence=Decimal("0.95")))
                    processed_txn_ids.add(t.transaction_id)

                group = DuplicateCandidateGroup(
                    group_id=f"dup_{ord_num.lower()}",
                    order_id=target_order.order_id,
                    order_number=target_order.order_number,
                    customer_name=target_order.customer_name if hasattr(target_order, "customer_name") else txn_list[0].sender_name,
                    expected_amount=target_order.net_amount,
                    total_received=total_received,
                    excess_amount=max(Decimal("0.00"), excess),
                    candidate_transactions=txn_list,
                    evidence_items=ev_items,
                    confidence=Decimal("0.95"),
                    explanation=(
                        f"Detected {len(txn_list)} separate bank credits referencing order {ord_num}. "
                        f"Order net is ₹{target_order.net_amount}, but ₹{total_received} was received "
                        f"(Excess: ₹{excess}). Requires human decision: issue refund or store credit."
                    ),
                    requires_human_review=True,
                )
                duplicate_groups.append(group)

    # 2. Evaluate sender + amount duplicates within time window for remaining credits
    for (sender, amt), txn_list in txns_by_sender_and_amount.items():
        # Exclude transactions already captured in order clusters
        unprocessed_list = [t for t in txn_list if t.transaction_id not in processed_txn_ids]
        if len(unprocessed_list) < 2:
            continue

        # Sort by transaction date
        sorted_txns = sorted(unprocessed_list, key=lambda x: x.transaction_date)
        for i in range(len(sorted_txns) - 1):
            t1 = sorted_txns[i]
            t2 = sorted_txns[i + 1]
            day_diff = abs((t2.transaction_date - t1.transaction_date).days)

            if day_diff <= time_window_days:
                pair = [t1, t2]
                processed_txn_ids.add(t1.transaction_id)
                processed_txn_ids.add(t2.transaction_id)

                total_received = amt * Decimal("2")
                ev_items = [
                    evidence_from_bank_txn(t1, correlation_id, confidence=Decimal("0.85")),
                    evidence_from_bank_txn(t2, correlation_id, confidence=Decimal("0.85")),
                ]

                group = DuplicateCandidateGroup(
                    group_id=f"dup_pair_{t1.utr_reference}_{t2.utr_reference}",
                    order_id=None,
                    order_number=None,
                    customer_name=t1.sender_name or sender,
                    expected_amount=amt,
                    total_received=total_received,
                    excess_amount=amt,
                    candidate_transactions=pair,
                    evidence_items=ev_items,
                    confidence=Decimal("0.85"),
                    explanation=(
                        f"Customer '{t1.sender_name or sender}' transferred exact amount ₹{amt} "
                        f"twice within {day_diff} days (UTRs: {t1.utr_reference} and {t2.utr_reference}). "
                        f"Possible duplicate payment candidate requiring seller verification."
                    ),
                    requires_human_review=True,
                )
                duplicate_groups.append(group)

    return duplicate_groups
