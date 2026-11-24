"""
Unit and Integration tests for Jarvis Deterministic Reconciliation Engine.
Verifies CSV normalization, column mapping, exact matches, partial payments,
duplicate payments, refunds, ambiguous matches, unmatched item audit metadata, and error handling.
"""

import os
from datetime import date
from decimal import Decimal
import pytest

from app.contracts.enums import CaseStatus, PaymentStatus, Severity
from app.contracts.errors import ErrorCode, JarvisContractException
from app.contracts.models import (
    BankTransaction,
    InvoiceRecord,
    OrderRecord,
)
from app.services.normalizer import (
    map_columns,
    normalize_bank_statement,
    normalize_invoices,
    normalize_orders,
    normalize_settlement_report,
    parse_date_flexible,
    parse_indian_money,
)
from app.services.reconciler import (
    DeterministicReconciler,
    MatchResult,
    ReconciliationReport,
    UnmatchedItem,
    calculate_name_similarity,
)


# -----------------------------------------------------------------------------
# 1. Normalization & Parsing Tests
# -----------------------------------------------------------------------------
def test_parse_indian_money():
    """Verify Indian currency symbols, commas, and negative notations parse to Decimal."""
    assert parse_indian_money("₹3,200.00") == Decimal("3200.00")
    assert parse_indian_money("Rs. 1,850") == Decimal("1850.00")
    assert parse_indian_money("INR 12,450.50") == Decimal("12450.50")
    assert parse_indian_money("-1950.00") == Decimal("-1950.00")
    assert parse_indian_money("(550.00)") == Decimal("-550.00")
    assert parse_indian_money("0") == Decimal("0.00")


def test_parse_flexible_dates():
    """Verify Indian date formats (DD/MM/YYYY) and ISO dates parse to date."""
    assert parse_date_flexible("01/10/2024") == date(2024, 10, 1)
    assert parse_date_flexible("15-10-2024") == date(2024, 10, 15)
    assert parse_date_flexible("2024-10-05") == date(2024, 10, 5)
    assert parse_date_flexible("18/10/24") == date(2024, 10, 18)


def test_missing_required_column_raises_contract_exception():
    """Verify missing required columns raise JarvisContractException with MISSING_REQUIRED_COLUMN."""
    bad_csv = "order_id,gross_amount\nORD-001,1500.00"
    with pytest.raises(JarvisContractException) as exc_info:
        normalize_orders(bad_csv, correlation_id="test_corr_err", source_filename="orders.csv")

    assert exc_info.value.code == ErrorCode.MISSING_REQUIRED_COLUMN
    assert "missing required column" in exc_info.value.message.lower()


def test_empty_or_corrupt_csv_raises_file_parse_error():
    """Verify empty CSV raises FILE_PARSE_ERROR."""
    with pytest.raises(JarvisContractException) as exc_info:
        normalize_orders("   ", correlation_id="test_corr_err", source_filename="empty.csv")

    assert exc_info.value.code == ErrorCode.FILE_PARSE_ERROR


# -----------------------------------------------------------------------------
# 2. Reconciler Core Logic Tests
# -----------------------------------------------------------------------------
def test_exact_match_with_order_reference():
    """
    Test 1:1 exact amount match where order number appears explicitly in bank narration.
    Score: 1.00, Status: PAID.
    """
    orders = [
        OrderRecord(
            order_id="ord_1001",
            correlation_id="corr_test",
            order_number="ORD-2024-1001",
            channel="WhatsApp",
            customer_id="CUST-1001",
            order_date=date(2024, 10, 1),
            gross_amount=Decimal("3200.00"),
            discount_amount=Decimal("0.00"),
            net_amount=Decimal("3200.00"),
            status="DELIVERED",
        )
    ]
    invoices = [
        InvoiceRecord(
            invoice_id="inv_201",
            correlation_id="corr_test",
            order_id="ord_1001",
            invoice_number="INV-2024-201",
            invoice_date=date(2024, 10, 1),
            subtotal=Decimal("3047.62"),
            tax_amount=Decimal("152.38"),
            total_amount=Decimal("3200.00"),
        )
    ]
    bank_txns = [
        BankTransaction(
            transaction_id="txn_1001",
            correlation_id="corr_test",
            transaction_date=date(2024, 10, 1),
            transaction_type="UPI_CR",
            amount=Decimal("3200.00"),
            utr_reference="4289001001",
            sender_name="Priya Sharma",
            sender_upi_id="priya@okhdfcbank",
            raw_narration="UPI/CR/4289001001/ORD-2024-1001/InstantTransfer",
        )
    ]

    reconciler = DeterministicReconciler(orders, invoices, bank_txns, correlation_id="corr_test")
    report = reconciler.reconcile()

    assert report.metrics["exact_matches"] == 1
    assert len(report.matches) == 1
    match = report.matches[0]
    assert match.matched_order_id == "ord_1001"
    assert match.matched_invoice_id == "inv_201"
    assert match.match_score == Decimal("1.00")
    assert match.status == PaymentStatus.PAID
    assert match.shortfall_amount == Decimal("0.00")
    assert "Exact match" in match.human_readable_explanation


def test_partial_payment_matching():
    """
    Test partial payment where customer paid advance (₹1,400) for a ₹1,850 order.
    Status: PARTIALLY_PAID, Shortfall: ₹450.00, Case created.
    """
    orders = [
        OrderRecord(
            order_id="ord_1014",
            correlation_id="corr_test",
            order_number="ORD-2024-1014",
            channel="Instagram",
            customer_id="CUST-1005",
            order_date=date(2024, 10, 14),
            gross_amount=Decimal("1850.00"),
            discount_amount=Decimal("0.00"),
            net_amount=Decimal("1850.00"),
            status="DELIVERED",
        )
    ]
    bank_txns = [
        BankTransaction(
            transaction_id="txn_1014",
            correlation_id="corr_test",
            transaction_date=date(2024, 10, 14),
            transaction_type="UPI_CR",
            amount=Decimal("1400.00"),
            utr_reference="4289001014",
            sender_name="Sneha Rao",
            sender_upi_id="sneha@okhdfcbank",
            raw_narration="UPI/CR/4289001014/ORD-2024-1014/AdvancePayment_1400",
        )
    ]

    reconciler = DeterministicReconciler(orders, [], bank_txns, correlation_id="corr_test")
    report = reconciler.reconcile()

    assert report.metrics["partial_matches"] == 1
    match = report.matches[0]
    assert match.status == PaymentStatus.PARTIALLY_PAID
    assert match.paid_amount == Decimal("1400.00")
    assert match.shortfall_amount == Decimal("450.00")
    assert len(report.cases) == 1
    case = report.cases[0]
    assert case.case_type == "PAYMENT_SHORTFALL"
    assert case.discrepancy_amount == Decimal("450.00")
    assert case.severity == Severity.HIGH  # Delivered order with shortfall


def test_duplicate_payment_detection_and_human_review():
    """
    Test duplicate transfer detection where customer paid ₹1,250 twice for ORD-2024-1008.
    Status: DUPLICATE_CANDIDATE, needs_review: True, Case created. Never auto-refunds.
    """
    orders = [
        OrderRecord(
            order_id="ord_1008",
            correlation_id="corr_test",
            order_number="ORD-2024-1008",
            channel="WhatsApp",
            customer_id="CUST-1004",
            order_date=date(2024, 10, 4),
            gross_amount=Decimal("1250.00"),
            discount_amount=Decimal("0.00"),
            net_amount=Decimal("1250.00"),
            status="DELIVERED",
        )
    ]
    bank_txns = [
        BankTransaction(
            transaction_id="txn_1008_1",
            correlation_id="corr_test",
            transaction_date=date(2024, 10, 4),
            transaction_type="UPI_CR",
            amount=Decimal("1250.00"),
            utr_reference="4289001008",
            sender_name="Kavita Patel",
            sender_upi_id="kavita@okaxis",
            raw_narration="UPI/CR/4289001008/ORD-2024-1008/Payment_1",
        ),
        BankTransaction(
            transaction_id="txn_1008_2",
            correlation_id="corr_test",
            transaction_date=date(2024, 10, 5),
            transaction_type="UPI_CR",
            amount=Decimal("1250.00"),
            utr_reference="4289001009",
            sender_name="Kavita Patel",
            sender_upi_id="kavita@okaxis",
            raw_narration="UPI/CR/4289001009/ORD-2024-1008/DuplicateTransfer",
        ),
    ]

    reconciler = DeterministicReconciler(orders, [], bank_txns, correlation_id="corr_test")
    report = reconciler.reconcile()

    assert report.metrics["duplicate_candidates"] == 1
    assert len(report.duplicate_groups) == 1
    dup_group = report.duplicate_groups[0]
    assert dup_group.excess_amount == Decimal("1250.00")
    assert dup_group.total_received == Decimal("2500.00")
    assert dup_group.requires_human_review is True

    # Validate that case is created in NEEDS_APPROVAL state
    assert len(report.cases) == 1
    case = report.cases[0]
    assert case.case_type == "DUPLICATE_PAYMENT_CANDIDATE"
    assert case.status == CaseStatus.NEEDS_APPROVAL


def test_refund_matching_cancelled_order():
    """
    Test debit refund matching for a cancelled order (₹1,950 debit).
    Status: REFUND_MATCH.
    """
    orders = [
        OrderRecord(
            order_id="ord_1029",
            correlation_id="corr_test",
            order_number="ORD-2024-1029",
            channel="WhatsApp",
            customer_id="CUST-1010",
            order_date=date(2024, 10, 18),
            gross_amount=Decimal("1950.00"),
            discount_amount=Decimal("0.00"),
            net_amount=Decimal("1950.00"),
            status="CANCELLED",
        )
    ]
    bank_txns = [
        BankTransaction(
            transaction_id="txn_deb_1029",
            correlation_id="corr_test",
            transaction_date=date(2024, 10, 22),
            transaction_type="UPI_DR",
            amount=Decimal("1950.00"),
            utr_reference="4289001032",
            sender_name="Aura Weaves Refund Desk",
            sender_upi_id="refund@icici",
            raw_narration="UPI/DR/4289001032/REFUND_ORD-2024-1029/SizeMismatchReturn",
        )
    ]

    reconciler = DeterministicReconciler(orders, [], bank_txns, correlation_id="corr_test")
    report = reconciler.reconcile()

    assert report.metrics["refund_matches"] == 1
    match = report.matches[0]
    assert match.status == PaymentStatus.REFUND_MATCH
    assert match.matched_order_id == "ord_1029"


def test_ambiguous_payment_matching_marked_needs_review():
    """
    Test ambiguous match where one bank credit matches two different orders with identical amounts
    and identical customer name within date window. Must NEVER auto-resolve.
    Status: UNMATCHED_CREDIT, is_ambiguous: True, needs_review: True.
    """
    orders = [
        OrderRecord(
            order_id="ord_a",
            correlation_id="corr_test",
            order_number="ORD-2024-9001",
            channel="Website",
            customer_id="Pooja Sharma",
            order_date=date(2024, 10, 10),
            gross_amount=Decimal("1500.00"),
            discount_amount=Decimal("0.00"),
            net_amount=Decimal("1500.00"),
            status="PLACED",
        ),
        OrderRecord(
            order_id="ord_b",
            correlation_id="corr_test",
            order_number="ORD-2024-9002",
            channel="Instagram",
            customer_id="Pooja Sharma",
            order_date=date(2024, 10, 11),
            gross_amount=Decimal("1500.00"),
            discount_amount=Decimal("0.00"),
            net_amount=Decimal("1500.00"),
            status="PLACED",
        ),
    ]
    # Bank credit without order reference in narration
    bank_txns = [
        BankTransaction(
            transaction_id="txn_ambig_1",
            correlation_id="corr_test",
            transaction_date=date(2024, 10, 11),
            transaction_type="UPI_CR",
            amount=Decimal("1500.00"),
            utr_reference="4289999999",
            sender_name="Pooja Sharma",
            sender_upi_id="pooja@okaxis",
            raw_narration="UPI/CR/4289999999/DirectPayment",  # No order ID!
        )
    ]

    reconciler = DeterministicReconciler(orders, [], bank_txns, correlation_id="corr_test")
    report = reconciler.reconcile()

    assert report.metrics["ambiguous_matches"] == 1
    match = report.matches[0]
    assert match.is_ambiguous is True
    assert match.needs_review is True
    assert match.status == PaymentStatus.UNMATCHED_CREDIT
    assert len(report.cases) == 1
    case = report.cases[0]
    assert case.case_type == "AMBIGUOUS_PAYMENT_MATCH"
    assert case.status == CaseStatus.INVESTIGATING


def test_unmatched_items_audit_reporting():
    """
    Verify unmatched credits and unmatched orders return what is missing,
    likely explanations, required evidence, and recommended next action.
    """
    orders = [
        OrderRecord(
            order_id="ord_unpaid",
            correlation_id="corr_test",
            order_number="ORD-2024-UNPAID",
            channel="Website",
            customer_id="Deepak Verma",
            order_date=date(2024, 10, 20),
            gross_amount=Decimal("2800.00"),
            discount_amount=Decimal("0.00"),
            net_amount=Decimal("2800.00"),
            status="SHIPPED",
        )
    ]
    bank_txns = [
        BankTransaction(
            transaction_id="txn_unknown",
            correlation_id="corr_test",
            transaction_date=date(2024, 10, 25),
            transaction_type="UPI_CR",
            amount=Decimal("999.00"),
            utr_reference="999888777",
            sender_name="Random Remitter",
            sender_upi_id="random@paytm",
            raw_narration="UPI/CR/999888777/RandomTransfer",
        )
    ]

    reconciler = DeterministicReconciler(orders, [], bank_txns, correlation_id="corr_test")
    report = reconciler.reconcile()

    assert len(report.unmatched_items) == 2

    # Unmatched bank credit
    txn_item = next(u for u in report.unmatched_items if u.item_type == "BANK_TRANSACTION")
    assert txn_item.amount == Decimal("999.00")
    assert txn_item.what_is_missing != ""
    assert len(txn_item.likely_explanations) > 0
    assert len(txn_item.required_evidence) > 0
    assert txn_item.recommended_next_action != ""

    # Unmatched order
    ord_item = next(u for u in report.unmatched_items if u.item_type == "ORDER")
    assert ord_item.amount == Decimal("2800.00")
    assert ord_item.what_is_missing != ""
    assert len(ord_item.likely_explanations) > 0
    assert len(ord_item.required_evidence) > 0
    assert "payment reminder" in ord_item.recommended_next_action.lower()


# -----------------------------------------------------------------------------
# 3. End-to-End Integration Test with Synthetic Demo Dataset Files
# -----------------------------------------------------------------------------
def test_full_dataset_reconciliation_integration():
    """
    Ingests actual files from data/ directory and runs the deterministic reconciliation engine.
    Verifies matching across 60 orders, 50 bank transactions, and 10 invoices.
    """
    data_dir = "C:/Users/ahaad/.gemini/antigravity/scratch/jarvis/data"
    orders_path = os.path.join(data_dir, "orders.csv")
    invoices_path = os.path.join(data_dir, "invoices.csv")
    bank_path = os.path.join(data_dir, "bank_statement.csv")
    settlement_path = os.path.join(data_dir, "settlement_report.csv")

    assert os.path.exists(orders_path)
    assert os.path.exists(invoices_path)
    assert os.path.exists(bank_path)
    assert os.path.exists(settlement_path)

    corr_id = "test_e2e_dataset_run"

    # 1. Normalize
    orders = normalize_orders(orders_path, corr_id)
    invoices = normalize_invoices(invoices_path, corr_id)
    bank_txns = normalize_bank_statement(bank_path, corr_id)
    settlements = normalize_settlement_report(settlement_path, corr_id)

    assert len(orders) == 60
    assert len(invoices) == 10
    assert len(bank_txns) == 50
    assert len(settlements) == 1

    # 2. Reconcile
    reconciler = DeterministicReconciler(orders, invoices, bank_txns, corr_id)
    report = reconciler.reconcile()

    # Verify metric guarantees
    assert report.metrics["total_orders"] == 60
    assert report.metrics["total_bank_transactions"] == 50
    assert report.metrics["partial_matches"] == 3
    assert report.metrics["duplicate_candidates"] == 2
    assert report.metrics["refund_matches"] == 1
    assert report.metrics["exact_matches"] >= 38
    assert len(report.cases) >= 5

    # Check that Sneha Rao's partial payment is detected with ₹450 shortfall
    sneha_match = next((m for m in report.matches if m.matched_order_id == "ord_ord-2024-1014"), None)
    assert sneha_match is not None
    assert sneha_match.status == PaymentStatus.PARTIALLY_PAID
    assert sneha_match.paid_amount == Decimal("1400.00")
    assert sneha_match.shortfall_amount == Decimal("450.00")
