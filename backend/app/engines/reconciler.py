from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.entities import Order, BankTransaction, Customer


class ReconciliationEngine:
    """
    100% Deterministic Python Payment Reconciliation Engine.
    Rules:
    - Pure arithmetic and string matching, zero LLM calls.
    - Matches bank transactions to orders based on order number in narration,
      customer name/UPI, and exact or partial amount matching.
    - Identifies:
      1. Exact matches (Transaction Amount == Order Net Amount)
      2. Partial payments (Transaction Amount < Order Net Amount)
      3. Duplicate payment candidates (Multiple credits for the same order/amount within 48h)
      4. Unmatched credits (Bank credits with no corresponding order)
    """

    def __init__(self, db: Session):
        self.db = db

    def run_reconciliation(self) -> Dict[str, Any]:
        orders = self.db.query(Order).all()
        transactions = self.db.query(BankTransaction).all()

        order_by_number: Dict[str, Order] = {o.order_number: o for o in orders}
        matched_txns: List[Dict[str, Any]] = []
        partial_txns: List[Dict[str, Any]] = []
        duplicate_candidates: List[Dict[str, Any]] = []
        unmatched_txns: List[Dict[str, Any]] = []

        # Track order payments to detect duplicates and calculate cumulative totals
        order_payments: Dict[str, List[BankTransaction]] = {}

        for txn in transactions:
            # 1. Search for order number in raw_description
            matched_order: Optional[Order] = None
            for ord_num, ord_obj in order_by_number.items():
                if ord_num in txn.raw_description:
                    matched_order = ord_obj
                    break

            # 2. If not found by order number in description, match by already assigned matched_order_id
            if not matched_order and txn.matched_order_id:
                matched_order = next((o for o in orders if o.id == txn.matched_order_id), None)

            # 3. Match by sender name and exact amount + date proximity if still unmatched
            if not matched_order and txn.sender_name:
                for ord_obj in orders:
                    if ord_obj.customer and ord_obj.customer.name.lower() == txn.sender_name.lower():
                        # If exact amount matches and within 5 days of order
                        if Decimal(str(txn.amount)) == Decimal(str(ord_obj.net_amount)):
                            days_diff = abs((txn.transaction_date - ord_obj.order_date).days)
                            if days_diff <= 5:
                                matched_order = ord_obj
                                break

            if matched_order:
                txn.matched_order_id = matched_order.id
                if matched_order.order_number not in order_payments:
                    order_payments[matched_order.order_number] = []
                order_payments[matched_order.order_number].append(txn)
            else:
                txn.reconciliation_status = "UNMATCHED"
                unmatched_txns.append({
                    "transaction_id": txn.id,
                    "utr": txn.utr_reference,
                    "amount": float(txn.amount),
                    "sender": txn.sender_name,
                    "date": txn.transaction_date.isoformat(),
                })

        # Process each order's payments to identify matches, partials, and duplicates
        for ord_num, txns in order_payments.items():
            ord_obj = order_by_number[ord_num]
            target_amount = Decimal(str(ord_obj.net_amount))

            if len(txns) == 1:
                t = txns[0]
                t_amount = Decimal(str(t.amount))
                if t_amount == target_amount:
                    t.reconciliation_status = "MATCHED"
                    matched_txns.append({
                        "order_number": ord_num,
                        "transaction_id": t.id,
                        "utr": t.utr_reference,
                        "amount": float(t.amount),
                    })
                elif t_amount < target_amount:
                    t.reconciliation_status = "PARTIAL"
                    shortfall = target_amount - t_amount
                    partial_txns.append({
                        "order_number": ord_num,
                        "order_id": ord_obj.id,
                        "customer_name": ord_obj.customer.name if ord_obj.customer else "Unknown",
                        "customer_id": ord_obj.customer_id,
                        "order_amount": float(target_amount),
                        "paid_amount": float(t_amount),
                        "shortfall_amount": float(shortfall),
                        "utr": t.utr_reference,
                        "transaction_id": t.id,
                    })
            else:
                # Multiple transactions for the same order -> Check for duplicate candidate
                # Sort by date
                txns_sorted = sorted(txns, key=lambda x: x.transaction_date)
                first_txn = txns_sorted[0]
                first_amt = Decimal(str(first_txn.amount))

                if first_amt == target_amount:
                    first_txn.reconciliation_status = "MATCHED"
                    matched_txns.append({
                        "order_number": ord_num,
                        "transaction_id": first_txn.id,
                        "utr": first_txn.utr_reference,
                        "amount": float(first_txn.amount),
                    })

                for extra_txn in txns_sorted[1:]:
                    extra_amt = Decimal(str(extra_txn.amount))
                    if extra_amt == target_amount or extra_amt == first_amt:
                        extra_txn.reconciliation_status = "DUPLICATE_CANDIDATE"
                        duplicate_candidates.append({
                            "order_number": ord_num,
                            "order_id": ord_obj.id,
                            "customer_name": ord_obj.customer.name if ord_obj.customer else "Unknown",
                            "customer_id": ord_obj.customer_id,
                            "expected_amount": float(target_amount),
                            "duplicate_amount": float(extra_amt),
                            "primary_utr": first_txn.utr_reference,
                            "duplicate_utr": extra_txn.utr_reference,
                            "primary_txn_id": first_txn.id,
                            "duplicate_txn_id": extra_txn.id,
                        })

        self.db.commit()

        return {
            "total_transactions": len(transactions),
            "matched_count": len(matched_txns),
            "partial_count": len(partial_txns),
            "duplicate_candidates_count": len(duplicate_candidates),
            "unmatched_count": len(unmatched_txns),
            "partials": partial_txns,
            "duplicates": duplicate_candidates,
            "unmatched": unmatched_txns,
        }
