import json
from decimal import Decimal
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.entities import Order, BankTransaction, Customer, SettlementReport
from app.models.promises import Promise
from app.models.cases import Case, CaseEvidence, PendingAction
from app.engines.reconciler import ReconciliationEngine
from app.engines.variance import VarianceEngine


class CaseSynthesizer:
    """
    Synthesizes findings from Reconciler, VarianceEngine, and Promises
    into unified, evidence-linked 'Cases' with proposed pending actions.
    """

    def __init__(self, db: Session):
        self.db = db

    def synthesize_all_cases(self) -> List[Case]:
        # 1. Run deterministic reconciliation
        reconciler = ReconciliationEngine(self.db)
        recon_result = reconciler.run_reconciliation()

        # 2. Run deterministic settlement variance
        variance_engine = VarianceEngine(self.db)
        variance_results = variance_engine.analyze_all_settlements()

        created_cases: List[Case] = []

        # A. Handle Partial Payments
        for p in recon_result["partials"]:
            order = self.db.query(Order).filter(Order.id == p["order_id"]).first()
            existing_case = self.db.query(Case).filter(
                Case.case_type == "PAYMENT_SHORTFALL",
                Case.order_id == p["order_id"]
            ).first()

            if not existing_case:
                c = Case(
                    title=f"Payment Shortfall on {p['order_number']}",
                    case_type="PAYMENT_SHORTFALL",
                    severity="HIGH",
                    status="OPEN",
                    customer_id=p["customer_id"],
                    order_id=p["order_id"],
                    discrepancy_amount=Decimal(str(p["shortfall_amount"])),
                    headline=f"Customer {p['customer_name']} paid ₹{p['paid_amount']} instead of ₹{p['order_amount']}",
                    explanation=(
                        f"Order {p['order_number']} total is ₹{p['order_amount']}. "
                        f"UPI credit {p['utr']} received on {order.order_date.isoformat()} was only ₹{p['paid_amount']}, "
                        f"leaving an unpaid balance of ₹{p['shortfall_amount']}."
                    ),
                )
                self.db.add(c)
                self.db.flush()

                # Evidence: Order
                ev_order = CaseEvidence(
                    case_id=c.id,
                    evidence_type="ORDER",
                    source_table="orders",
                    source_id=order.id,
                    content_payload={
                        "order_number": order.order_number,
                        "net_amount": float(order.net_amount),
                        "channel": order.channel,
                        "date": order.order_date.isoformat(),
                    },
                )
                self.db.add(ev_order)

                # Evidence: Bank Txn
                ev_txn = CaseEvidence(
                    case_id=c.id,
                    evidence_type="BANK_TXN",
                    source_table="bank_transactions",
                    source_id=p["transaction_id"],
                    content_payload={
                        "utr": p["utr"],
                        "amount_received": p["paid_amount"],
                        "shortfall": p["shortfall_amount"],
                    },
                )
                self.db.add(ev_txn)

                # Proposed Pending Action: Razorpay Payment Link for Shortfall
                action = PendingAction(
                    case_id=c.id,
                    action_type="RAZORPAY_PAYMENT_LINK",
                    target_recipient=order.customer.phone if order.customer else "+919800000000",
                    action_summary=f"Generate Razorpay Test Payment Link for unpaid ₹{p['shortfall_amount']}",
                    payload={
                        "amount": float(p["shortfall_amount"]),
                        "currency": "INR",
                        "description": f"Balance payment for {p['order_number']}",
                        "customer": {
                            "name": p["customer_name"],
                            "contact": order.customer.phone if order.customer else "",
                            "email": order.customer.email if order.customer else "",
                        },
                    },
                    status="PENDING",
                )
                self.db.add(action)
                created_cases.append(c)

        # B. Handle Duplicate Payment Candidates
        for d in recon_result["duplicates"]:
            order = self.db.query(Order).filter(Order.id == d["order_id"]).first()
            existing_case = self.db.query(Case).filter(
                Case.case_type == "DUPLICATE_PAYMENT",
                Case.order_id == d["order_id"]
            ).first()

            if not existing_case:
                c = Case(
                    title=f"Potential Duplicate Payment on {d['order_number']}",
                    case_type="DUPLICATE_PAYMENT",
                    severity="CRITICAL",
                    status="OPEN",
                    customer_id=d["customer_id"],
                    order_id=d["order_id"],
                    discrepancy_amount=Decimal(str(d["duplicate_amount"])),
                    headline=f"Customer {d['customer_name']} paid ₹{d['duplicate_amount']} twice for {d['order_number']}",
                    explanation=(
                        f"Order {d['order_number']} was paid via UTR {d['primary_utr']}. "
                        f"A second credit of identical amount ₹{d['duplicate_amount']} arrived via UTR {d['duplicate_utr']}. "
                        f"Customer likely paid twice due to bank app latency."
                    ),
                )
                self.db.add(c)
                self.db.flush()

                # Evidence: Primary Txn
                ev1 = CaseEvidence(
                    case_id=c.id,
                    evidence_type="BANK_TXN",
                    source_table="bank_transactions",
                    source_id=d["primary_txn_id"],
                    content_payload={"utr": d["primary_utr"], "amount": d["duplicate_amount"], "status": "PRIMARY"},
                )
                self.db.add(ev1)

                # Evidence: Duplicate Txn
                ev2 = CaseEvidence(
                    case_id=c.id,
                    evidence_type="BANK_TXN",
                    source_table="bank_transactions",
                    source_id=d["duplicate_txn_id"],
                    content_payload={"utr": d["duplicate_utr"], "amount": d["duplicate_amount"], "status": "DUPLICATE"},
                )
                self.db.add(ev2)

                # Proposed Pending Action: Gmail Draft informing customer
                action = PendingAction(
                    case_id=c.id,
                    action_type="GMAIL_DRAFT",
                    target_recipient=order.customer.email or f"{order.customer.name.lower().replace(' ', '')}@example.com",
                    action_summary=f"Draft email to {d['customer_name']} regarding duplicate ₹{d['duplicate_amount']} transfer",
                    payload={
                        "subject": f"Notice regarding duplicate transfer for Order {d['order_number']}",
                        "recipient": order.customer.email or "customer@example.com",
                        "body": (
                            f"Dear {d['customer_name']},\n\n"
                            f"We noticed two separate transfers of ₹{d['duplicate_amount']} for your order {d['order_number']} "
                            f"(UTRs: {d['primary_utr']} and {d['duplicate_utr']}).\n"
                            f"Please confirm if you would like an instant refund to your source account or store credit.\n\n"
                            f"Warm regards,\nAura Weaves & Jewels"
                        ),
                    },
                    status="PENDING",
                )
                self.db.add(action)
                created_cases.append(c)

        # C. Handle Marketplace Settlement Variances
        for v in variance_results:
            if v["has_unexplained_variance"]:
                existing_case = self.db.query(Case).filter(
                    Case.case_type == "MARKETPLACE_VARIANCE",
                    Case.title.like(f"%{v['settlement_id']}%")
                ).first()

                if not existing_case:
                    c = Case(
                        title=f"Unexplained Deduction Variance on {v['marketplace']} ({v['settlement_id']})",
                        case_type="MARKETPLACE_VARIANCE",
                        severity="HIGH",
                        status="OPEN",
                        customer_id=None,
                        order_id=None,
                        discrepancy_amount=Decimal(str(v["unexplained_residual"])),
                        headline=f"₹{v['unexplained_residual']} shortfall between expected payout and bank credit",
                        explanation=(
                            f"For settlement period {v['period']}, gross sales were ₹{v['gross_order_value']}. "
                            f"Total itemized deductions (commission, logistics, RTO, taxes) were ₹{v['total_known_deductions']}. "
                            f"Calculated expected net payout was ₹{v['calculated_expected_payout']}, but bank credit received was ₹{v['actual_bank_credit']}. "
                            f"Unexplained residual deduction of ₹{v['unexplained_residual']} identified."
                        ),
                    )
                    self.db.add(c)
                    self.db.flush()

                    # Evidence: Settlement Waterfall
                    ev_settle = CaseEvidence(
                        case_id=c.id,
                        evidence_type="SETTLEMENT_LINE",
                        source_table="settlement_reports",
                        source_id=v["settlement_id"],
                        content_payload={
                            "waterfall": v["waterfall"],
                            "bank_utr": v["bank_utr"],
                            "residual": v["unexplained_residual"],
                        },
                    )
                    self.db.add(ev_settle)

                    # Proposed Action: Prepare Dispute Dossier / Draft
                    action = PendingAction(
                        case_id=c.id,
                        action_type="SETTLEMENT_DISPUTE_PACK",
                        target_recipient="seller-support@meesho.com",
                        action_summary=f"Prepare dispute dossier for ₹{v['unexplained_residual']} unexplained deduction",
                        payload={
                            "marketplace": v["marketplace"],
                            "settlement_id": v["settlement_id"],
                            "unexplained_amount": v["unexplained_residual"],
                            "bank_utr": v["bank_utr"],
                            "statement_period": v["period"],
                        },
                        status="PENDING",
                    )
                    self.db.add(action)
                    created_cases.append(c)

        # D. Handle Broken Delivery Promises
        broken_promises = self.db.query(Promise).filter(Promise.status == "BROKEN").all()
        for bp in broken_promises:
            existing_case = self.db.query(Case).filter(
                Case.case_type == "BROKEN_PROMISE",
                Case.order_id == bp.order_id
            ).first()

            if not existing_case and bp.order:
                order = bp.order
                c = Case(
                    title=f"Broken Delivery Commitment for {bp.customer.name} ({order.order_number})",
                    case_type="BROKEN_PROMISE",
                    severity="HIGH",
                    status="OPEN",
                    customer_id=bp.customer_id,
                    order_id=bp.order_id,
                    discrepancy_amount=Decimal("0.00"),
                    headline=f"Promised delivery by {bp.target_date.isoformat()} was delivered late on {order.actual_delivery_date.isoformat()}",
                    explanation=(
                        f"In WhatsApp conversation on {bp.timestamp.strftime('%d-%b')}, seller explicitly promised: "
                        f"'{bp.raw_message_snippet}'. The customer needed it for a Karwa Chauth event on Oct 18th. "
                        f"The shipment arrived on Oct 21st, 3 days after the event."
                    ),
                )
                self.db.add(c)
                self.db.flush()

                ev_chat = CaseEvidence(
                    case_id=c.id,
                    evidence_type="CHAT_SNIPPET",
                    source_table="promises",
                    source_id=bp.id,
                    content_payload={
                        "raw_snippet": bp.raw_message_snippet,
                        "promised_date": bp.target_date.isoformat(),
                        "actual_delivery": order.actual_delivery_date.isoformat(),
                    },
                )
                self.db.add(ev_chat)

                # Proposed Action: Gmail Draft with Apology and ₹200 Goodwill Voucher
                action = PendingAction(
                    case_id=c.id,
                    action_type="GMAIL_DRAFT",
                    target_recipient=bp.customer.email or "customer@example.com",
                    action_summary=f"Draft apology email with ₹200 goodwill voucher for late delivery",
                    payload={
                        "subject": f"Sincere apologies regarding your order {order.order_number}",
                        "recipient": bp.customer.email or "ananya.roy@example.com",
                        "body": (
                            f"Dear {bp.customer.name},\n\n"
                            f"We deeply apologize for the delay in delivering your Karwa Chauth outfit (Order {order.order_number}). "
                            f"We promised delivery by {bp.target_date.strftime('%d-%b')}, but our courier partner delayed dispatch until {order.actual_delivery_date.strftime('%d-%b')}.\n"
                            f"As a gesture of goodwill, please accept this ₹200 voucher code: APOLOGY200 for your next purchase.\n\n"
                            f"Warm regards,\nNeha (Aura Weaves & Jewels)"
                        ),
                    },
                    status="PENDING",
                )
                self.db.add(action)
                created_cases.append(c)

        # E. Handle Unrecorded Free Gifts
        unrecorded_gifts = self.db.query(Promise).filter(
            Promise.promise_type == "FREE_GIFT",
            Promise.status == "UNRECORDED"
        ).all()
        for ug in unrecorded_gifts:
            existing_case = self.db.query(Case).filter(
                Case.case_type == "UNRECORDED_GIFT",
                Case.customer_id == ug.customer_id
            ).first()

            if not existing_case and ug.order:
                order = ug.order
                c = Case(
                    title=f"Unrecorded Free Gift Promise for {ug.customer.name} ({order.order_number})",
                    case_type="UNRECORDED_GIFT",
                    severity="MEDIUM",
                    status="OPEN",
                    customer_id=ug.customer_id,
                    order_id=ug.order_id,
                    discrepancy_amount=Decimal("0.00"),
                    headline="Complimentary silk scrunchie promised in WhatsApp but omitted from order notes",
                    explanation=(
                        f"Seller promised customer {ug.customer.name} in WhatsApp: '{ug.raw_message_snippet}'. "
                        f"However, order {order.order_number} notes state: '{order.notes}', omitting the promised free scrunchie. "
                        f"Risk of customer disappointment upon unboxing."
                    ),
                )
                self.db.add(c)
                self.db.flush()

                ev_gift = CaseEvidence(
                    case_id=c.id,
                    evidence_type="PROMISE",
                    source_table="promises",
                    source_id=ug.id,
                    content_payload={
                        "promise_snippet": ug.raw_message_snippet,
                        "order_notes": order.notes,
                    },
                )
                self.db.add(ev_gift)

                action = PendingAction(
                    case_id=c.id,
                    action_type="GMAIL_DRAFT",
                    target_recipient="warehouse@auraweaves.com",
                    action_summary="Draft internal alert to packing desk to add free silk scrunchie to parcel",
                    payload={
                        "subject": f"URGENT: Add Free Gift to Order {order.order_number}",
                        "recipient": "packing@auraweaves.com",
                        "body": (
                            f"Packing Team:\n"
                            f"Please ensure a complimentary Peacock Blue Silk Scrunchie is packed inside parcel for "
                            f"Order {order.order_number} ({ug.customer.name}). Promised on WhatsApp.\n"
                        ),
                    },
                    status="PENDING",
                )
                self.db.add(action)
                created_cases.append(c)

        self.db.commit()
        return created_cases
