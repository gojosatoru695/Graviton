"""
Jarvis Deterministic Evidence Builder Service.
Constructs verifiable EvidenceItem artifacts linked to Orders, Bank Transactions,
Invoices, Settlement Lines, Deliveries, and Chat Messages.

Rules:
- Never treat confidence as proof. Deterministic links receive 1.00; fuzzy/heuristic receive strict <1.00 Decimal.
- Every evidence artifact must carry full source provenance (source_table, source_entity_id, source_file, line_number).
- Snapshot payloads are strictly preserved as immutable dictionaries.
"""

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional, Union

from app.contracts.enums import EvidenceType
from app.contracts.models import (
    BankTransaction,
    DeliveryRecord,
    EvidenceItem,
    InvoiceRecord,
    OrderRecord,
    SettlementLine,
)


def _safe_serialize(val: Any) -> Any:
    """Recursively converts Decimals and dates to strings for JSON payload serialization."""
    if isinstance(val, Decimal):
        return str(val)
    if hasattr(val, "isoformat"):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: _safe_serialize(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_safe_serialize(x) for x in val]
    return val


def create_evidence_item(
    correlation_id: str,
    evidence_type: EvidenceType,
    source_table: str,
    source_entity_id: str,
    snapshot_payload: Dict[str, Any],
    source_file: Optional[str] = None,
    source_line_number: Optional[int] = None,
    confidence: Decimal = Decimal("1.00"),
) -> EvidenceItem:
    """
    Constructs a validated EvidenceItem with deterministic ID generation.
    """
    # Deterministic ID based on source and entity
    raw_hash = hashlib.sha256(f"{source_table}:{source_entity_id}:{evidence_type.value}".encode()).hexdigest()[:12]
    evidence_id = f"evi_{source_table}_{raw_hash}"

    clean_payload = _safe_serialize(snapshot_payload)

    return EvidenceItem(
        evidence_id=evidence_id,
        correlation_id=correlation_id,
        evidence_type=evidence_type,
        source_table=source_table,
        source_entity_id=str(source_entity_id),
        source_file=source_file,
        source_line_number=source_line_number,
        snapshot_payload=clean_payload,
        confidence=confidence,
        created_at=datetime.now(timezone.utc),
    )


def evidence_from_order(
    order: OrderRecord,
    correlation_id: str,
    source_file: str = "orders.csv",
    line_number: Optional[int] = None,
) -> EvidenceItem:
    """Builds an EvidenceItem from an OrderRecord."""
    return create_evidence_item(
        correlation_id=correlation_id,
        evidence_type=EvidenceType.ORDER,
        source_table="orders",
        source_entity_id=order.order_number,
        source_file=source_file,
        source_line_number=line_number,
        confidence=Decimal("1.00"),
        snapshot_payload={
            "order_number": order.order_number,
            "channel": order.channel,
            "customer_id": order.customer_id,
            "order_date": order.order_date.isoformat(),
            "gross_amount": str(order.gross_amount),
            "discount_amount": str(order.discount_amount),
            "net_amount": str(order.net_amount),
            "status": order.status,
            "notes": order.notes,
        },
    )


def evidence_from_bank_txn(
    txn: BankTransaction,
    correlation_id: str,
    source_file: str = "bank_statement.csv",
    line_number: Optional[int] = None,
    confidence: Decimal = Decimal("1.00"),
) -> EvidenceItem:
    """Builds an EvidenceItem from a BankTransaction."""
    return create_evidence_item(
        correlation_id=correlation_id,
        evidence_type=EvidenceType.BANK_TXN,
        source_table="bank_transactions",
        source_entity_id=txn.transaction_id,
        source_file=source_file,
        source_line_number=line_number,
        confidence=confidence,
        snapshot_payload={
            "transaction_id": txn.transaction_id,
            "transaction_date": txn.transaction_date.isoformat(),
            "transaction_type": txn.transaction_type,
            "amount": str(txn.amount),
            "utr_reference": txn.utr_reference,
            "sender_name": txn.sender_name,
            "sender_upi_id": txn.sender_upi_id,
            "raw_narration": txn.raw_narration,
        },
    )


def evidence_from_invoice(
    invoice: InvoiceRecord,
    correlation_id: str,
    source_file: str = "invoices.csv",
    line_number: Optional[int] = None,
) -> EvidenceItem:
    """Builds an EvidenceItem from an InvoiceRecord."""
    return create_evidence_item(
        correlation_id=correlation_id,
        evidence_type=EvidenceType.INVOICE,
        source_table="invoices",
        source_entity_id=invoice.invoice_number,
        source_file=source_file,
        source_line_number=line_number,
        confidence=Decimal("1.00"),
        snapshot_payload={
            "invoice_number": invoice.invoice_number,
            "order_id": invoice.order_id,
            "invoice_date": invoice.invoice_date.isoformat(),
            "subtotal": str(invoice.subtotal),
            "tax_amount": str(invoice.tax_amount),
            "total_amount": str(invoice.total_amount),
            "document_uri": invoice.document_uri,
        },
    )


def evidence_from_settlement_line(
    settlement_dict: Dict[str, Any],
    correlation_id: str,
    source_file: str = "settlement_report.csv",
    line_number: Optional[int] = None,
) -> EvidenceItem:
    """Builds an EvidenceItem from a settlement line/report dictionary."""
    s_id = settlement_dict.get("settlement_id", "STMT-UNKNOWN")
    return create_evidence_item(
        correlation_id=correlation_id,
        evidence_type=EvidenceType.SETTLEMENT_LINE,
        source_table="settlement_reports",
        source_entity_id=s_id,
        source_file=source_file,
        source_line_number=line_number,
        confidence=Decimal("1.00"),
        snapshot_payload={
            "settlement_id": s_id,
            "marketplace": settlement_dict.get("marketplace"),
            "gross_order_value": str(settlement_dict.get("gross_order_value")),
            "commission_fee": str(settlement_dict.get("commission_fee")),
            "shipping_fee": str(settlement_dict.get("shipping_fee")),
            "return_rto_fee": str(settlement_dict.get("return_rto_fee")),
            "tax_deduction_tcs_tds": str(settlement_dict.get("tax_deduction_tcs_tds")),
            "other_known_adjustment": str(settlement_dict.get("other_known_adjustment")),
            "expected_net_payable": str(settlement_dict.get("expected_net_payable")),
            "actual_bank_credit": str(settlement_dict.get("actual_bank_credit")),
            "bank_utr_reference": settlement_dict.get("bank_utr_reference"),
            "unexplained_deductions": settlement_dict.get("unexplained_deductions", []),
        },
    )


def evidence_from_chat(
    speaker: str,
    timestamp_str: str,
    message: str,
    correlation_id: str,
    order_ref: Optional[str] = None,
    source_file: str = "whatsapp_export.txt",
    line_number: Optional[int] = None,
) -> EvidenceItem:
    """Builds an EvidenceItem from a customer or seller communication log."""
    msg_hash = hashlib.sha256(f"{timestamp_str}:{speaker}:{message}".encode()).hexdigest()[:10]
    return create_evidence_item(
        correlation_id=correlation_id,
        evidence_type=EvidenceType.CHAT_SNIPPET,
        source_table="communications",
        source_entity_id=f"chat_{msg_hash}",
        source_file=source_file,
        source_line_number=line_number,
        confidence=Decimal("1.00"),
        snapshot_payload={
            "speaker": speaker,
            "timestamp": timestamp_str,
            "message": message,
            "order_reference": order_ref,
        },
    )
