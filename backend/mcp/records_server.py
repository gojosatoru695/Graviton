"""
Jarvis Records FastMCP Server.

Exposes controlled, policy-cleared tools for querying and reconciling orders,
invoices, bank credits, marketplace settlements, and case evidence.

Rules:
- Validates inputs using strict Pydantic models.
- Returns structured, deterministic dictionaries.
- Parameterized scoped queries with pagination caps (never unrestricted DB access).
- Masks sensitive customer PII in logs and representations.
- Zero raw secrets exposed.
"""

import logging
import re
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from fastmcp import FastMCP

from app.database import SessionLocal
from app.models.entities import (
    Customer,
    Order,
    Invoice,
    BankTransaction,
    SettlementReport,
    SettlementLineItem,
)
from app.models.cases import Case, CaseEvidence
from app.contracts.enums import Severity, EvidenceType

logger = logging.getLogger("jarvis.mcp.records")
logging.basicConfig(level=logging.INFO)

mcp = FastMCP("Jarvis-Records-MCP")


# ---------------------------------------------------------------------------
# Helpers & Security Sanitization
# ---------------------------------------------------------------------------
def mask_pii(text: Optional[str]) -> str:
    """Masks phone numbers and emails in log records."""
    if not text:
        return ""
    # Mask phone
    s = re.sub(r"(\+?\d{2,4})?\d{6}(\d{2})", r"\1******\2", str(text))
    # Mask email
    s = re.sub(r"([^@\s]{2})[^@\s]+(@[^@\s]+)", r"\1***\2", s)
    return s


def log_tool_call(tool_name: str, **kwargs: Any) -> None:
    """Audit logs tool invocations without leaking sensitive values."""
    sanitized = {k: mask_pii(str(v)) if any(x in k.lower() for x in ["phone", "email", "recipient", "contact"]) else v for k, v in kwargs.items()}
    logger.info(f"[MCP:Records] {tool_name} invoked with args: {sanitized}")


# ---------------------------------------------------------------------------
# Input Contracts
# ---------------------------------------------------------------------------
class PaginationInput(BaseModel):
    limit: int = Field(50, ge=1, le=100, description="Max items to retrieve (capped at 100).")
    offset: int = Field(0, ge=0, description="Number of items to skip.")


class CreateCaseInput(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    case_type: str = Field(..., description="PAYMENT_SHORTFALL, DUPLICATE_PAYMENT, MARKETPLACE_VARIANCE, BROKEN_PROMISE, or UNRECORDED_GIFT")
    severity: str = Field(..., description="CRITICAL, HIGH, MEDIUM, or LOW")
    headline: str = Field(..., min_length=5)
    explanation: str = Field(..., min_length=10)
    discrepancy_amount: float = Field(0.0, ge=0.0)
    customer_id: Optional[str] = None
    order_id: Optional[str] = None

    @field_validator("case_type")
    @classmethod
    def validate_case_type(cls, v: str) -> str:
        valid = {"PAYMENT_SHORTFALL", "DUPLICATE_PAYMENT", "MARKETPLACE_VARIANCE", "BROKEN_PROMISE", "UNRECORDED_GIFT"}
        if v.upper() not in valid:
            raise ValueError(f"Invalid case_type '{v}'. Must be one of {valid}")
        return v.upper()

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        if v.upper() not in valid:
            raise ValueError(f"Invalid severity '{v}'. Must be one of {valid}")
        return v.upper()


class AddEvidenceInput(BaseModel):
    case_id: str = Field(..., min_length=1)
    evidence_type: str = Field(..., min_length=2)
    source_table: str = Field(..., min_length=2)
    source_id: str = Field(..., min_length=1)
    content_payload: Dict[str, Any]


# ---------------------------------------------------------------------------
# MCP Tools (Exact Required 10 Tools)
# ---------------------------------------------------------------------------
@mcp.tool()
def list_orders(limit: int = 50, offset: int = 0, status: Optional[str] = None) -> Dict[str, Any]:
    """Lists orders with pagination and optional status filter."""
    log_tool_call("list_orders", limit=limit, offset=offset, status=status)
    PaginationInput(limit=limit, offset=offset)

    db = SessionLocal()
    try:
        query = db.query(Order)
        if status:
            query = query.filter(Order.status == status.upper())
        total = query.count()
        orders = query.order_by(Order.order_date.desc()).offset(offset).limit(limit).all()

        return {
            "total_count": total,
            "returned_count": len(orders),
            "orders": [
                {
                    "order_id": o.id,
                    "order_number": o.order_number,
                    "channel": o.channel,
                    "order_date": o.order_date.isoformat(),
                    "net_amount": float(o.net_amount),
                    "gross_amount": float(o.gross_amount),
                    "discount_amount": float(o.discount_amount),
                    "status": o.status,
                    "customer_id": o.customer_id,
                    "tracking_number": o.tracking_number,
                }
                for o in orders
            ],
        }
    finally:
        db.close()


@mcp.tool()
def get_order(order_id_or_number: str) -> Dict[str, Any]:
    """Retrieves full order details by order ID or customer order number."""
    log_tool_call("get_order", order_id_or_number=order_id_or_number)
    db = SessionLocal()
    try:
        order = (
            db.query(Order)
            .filter((Order.id == order_id_or_number) | (Order.order_number == order_id_or_number))
            .first()
        )
        if not order:
            return {"found": False, "error": f"Order not found: {order_id_or_number}"}

        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        invoices = db.query(Invoice).filter(Invoice.order_id == order.id).all()
        txns = db.query(BankTransaction).filter(BankTransaction.matched_order_id == order.id).all()

        return {
            "found": True,
            "order": {
                "id": order.id,
                "order_number": order.order_number,
                "channel": order.channel,
                "order_date": order.order_date.isoformat(),
                "gross_amount": float(order.gross_amount),
                "discount_amount": float(order.discount_amount),
                "net_amount": float(order.net_amount),
                "status": order.status,
                "expected_delivery_date": order.expected_delivery_date.isoformat() if order.expected_delivery_date else None,
                "actual_delivery_date": order.actual_delivery_date.isoformat() if order.actual_delivery_date else None,
                "tracking_number": order.tracking_number,
                "customer": {
                    "id": customer.id if customer else None,
                    "name": customer.name if customer else "Unknown",
                    "phone": mask_pii(customer.phone) if customer else None,
                },
                "invoices": [{"invoice_number": inv.invoice_number, "total_amount": float(inv.total_amount)} for inv in invoices],
                "matched_bank_credits": [
                    {"utr": t.utr_reference, "amount": float(t.amount), "status": t.reconciliation_status}
                    for t in txns
                ],
            },
        }
    finally:
        db.close()


@mcp.tool()
def list_invoices(order_id: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """Lists commercial invoices, optionally filtered by order ID."""
    log_tool_call("list_invoices", order_id=order_id, limit=limit)
    db = SessionLocal()
    try:
        query = db.query(Invoice)
        if order_id:
            query = query.filter(Invoice.order_id == order_id)
        invoices = query.limit(min(limit, 100)).all()

        return {
            "count": len(invoices),
            "invoices": [
                {
                    "invoice_id": inv.id,
                    "order_id": inv.order_id,
                    "invoice_number": inv.invoice_number,
                    "invoice_date": inv.invoice_date.isoformat(),
                    "subtotal": float(inv.subtotal),
                    "tax_amount": float(inv.tax_amount),
                    "total_amount": float(inv.total_amount),
                    "pdf_path": inv.pdf_path,
                }
                for inv in invoices
            ],
        }
    finally:
        db.close()


@mcp.tool()
def list_bank_transactions(status: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """Lists bank & UPI credit entries with matching status filter."""
    log_tool_call("list_bank_transactions", status=status, limit=limit)
    db = SessionLocal()
    try:
        query = db.query(BankTransaction)
        if status:
            query = query.filter(BankTransaction.reconciliation_status == status.upper())
        txns = query.order_by(BankTransaction.transaction_date.desc()).limit(min(limit, 100)).all()

        return {
            "count": len(txns),
            "transactions": [
                {
                    "id": t.id,
                    "date": t.transaction_date.isoformat(),
                    "type": t.transaction_type,
                    "amount": float(t.amount),
                    "utr_reference": t.utr_reference,
                    "sender_name": t.sender_name,
                    "sender_upi_id": mask_pii(t.sender_upi_id),
                    "raw_description": t.raw_description,
                    "status": t.reconciliation_status,
                    "matched_order_id": t.matched_order_id,
                }
                for t in txns
            ],
        }
    finally:
        db.close()


@mcp.tool()
def list_settlement_lines(settlement_id: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    """Lists marketplace remittance line items and deductions breakdown."""
    log_tool_call("list_settlement_lines", settlement_id=settlement_id, limit=limit)
    db = SessionLocal()
    try:
        query = db.query(SettlementLineItem)
        if settlement_id:
            # Match internal UUID or platform settlement ID
            report = db.query(SettlementReport).filter(
                (SettlementReport.id == settlement_id) | (SettlementReport.settlement_id == settlement_id)
            ).first()
            if report:
                query = query.filter(SettlementLineItem.settlement_id == report.id)
            else:
                query = query.filter(SettlementLineItem.settlement_id == settlement_id)

        lines = query.limit(min(limit, 100)).all()
        return {
            "count": len(lines),
            "line_items": [
                {
                    "id": l.id,
                    "settlement_id": l.settlement_id,
                    "order_reference": l.order_reference,
                    "gross_amount": float(l.gross_amount),
                    "deductions_breakdown": l.deductions_breakdown,
                    "net_amount": float(l.net_amount),
                    "matched_order_id": l.matched_order_id,
                }
                for l in lines
            ],
        }
    finally:
        db.close()


@mcp.tool()
def match_payment_to_order(bank_txn_id: str, order_id: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """Reconciles a bank UPI credit against a specific order."""
    log_tool_call("match_payment_to_order", bank_txn_id=bank_txn_id, order_id=order_id)
    db = SessionLocal()
    try:
        txn = db.query(BankTransaction).filter(BankTransaction.id == bank_txn_id).first()
        if not txn:
            return {"success": False, "error": f"Bank transaction not found: {bank_txn_id}"}

        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"success": False, "error": f"Order not found: {order_id}"}

        # Determine reconciliation status (Full match vs Partial)
        order_net = Decimal(str(order.net_amount))
        credit_amt = Decimal(str(txn.amount))

        if credit_amt >= order_net:
            txn.reconciliation_status = "MATCHED"
        else:
            txn.reconciliation_status = "PARTIAL"

        txn.matched_order_id = order.id
        db.commit()

        return {
            "success": True,
            "bank_txn_id": txn.id,
            "order_id": order.id,
            "order_number": order.order_number,
            "reconciliation_status": txn.reconciliation_status,
            "credit_amount": float(txn.amount),
            "order_amount": float(order.net_amount),
            "shortfall": float(max(Decimal(0), order_net - credit_amt)),
            "notes": notes,
        }
    finally:
        db.close()


@mcp.tool()
def calculate_settlement_variance(settlement_id: str) -> Dict[str, Any]:
    """Calculates step-by-step remittance waterfall and residual variance for a marketplace payout."""
    log_tool_call("calculate_settlement_variance", settlement_id=settlement_id)
    db = SessionLocal()
    try:
        report = (
            db.query(SettlementReport)
            .filter((SettlementReport.id == settlement_id) | (SettlementReport.settlement_id == settlement_id))
            .first()
        )
        if not report:
            return {"error": f"Settlement report not found: {settlement_id}"}

        gross = Decimal(str(report.gross_order_value))
        commission = Decimal(str(report.commission_fee))
        logistics = Decimal(str(report.logistics_fee))
        penalties = Decimal(str(report.return_penalties))
        taxes = Decimal(str(report.taxes_tcs_tds))
        actual = Decimal(str(report.actual_bank_credit))

        contractual_deductions = commission + logistics + penalties + taxes
        calculated_net = gross - contractual_deductions
        unexplained_gap = calculated_net - actual

        return {
            "settlement_id": report.settlement_id,
            "marketplace": report.marketplace,
            "period": f"{report.period_start} to {report.period_end}",
            "waterfall": [
                {"step": "Gross Sales", "amount": float(gross), "type": "gross"},
                {"step": "Platform Commission", "amount": float(-commission), "type": "deduction"},
                {"step": "Logistics Fees", "amount": float(-logistics), "type": "deduction"},
                {"step": "Return Penalties", "amount": float(-penalties), "type": "deduction"},
                {"step": "Taxes (GST/TCS/TDS)", "amount": float(-taxes), "type": "deduction"},
                {"step": "Calculated Net Payable", "amount": float(calculated_net), "type": "subtotal"},
                {"step": "Unexplained Residual Variance", "amount": float(-unexplained_gap), "type": "residual"},
                {"step": "Actual Remitted to Bank", "amount": float(actual), "type": "actual"},
            ],
            "has_unexplained_variance": unexplained_gap != Decimal(0),
            "unexplained_gap": float(unexplained_gap),
        }
    finally:
        db.close()


@mcp.tool()
def create_case(
    title: str,
    case_type: str,
    severity: str,
    headline: str,
    explanation: str,
    discrepancy_amount: float = 0.0,
    customer_id: Optional[str] = None,
    order_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Creates a new reconciliation or broken commitment case."""
    log_tool_call("create_case", title=title, case_type=case_type, severity=severity)
    validated = CreateCaseInput(
        title=title,
        case_type=case_type,
        severity=severity,
        headline=headline,
        explanation=explanation,
        discrepancy_amount=discrepancy_amount,
        customer_id=customer_id,
        order_id=order_id,
    )

    db = SessionLocal()
    try:
        case = Case(
            id=f"case_{uuid.uuid4().hex[:8]}",
            title=validated.title,
            case_type=validated.case_type,
            severity=validated.severity,
            headline=validated.headline,
            explanation=validated.explanation,
            discrepancy_amount=Decimal(str(validated.discrepancy_amount)),
            customer_id=validated.customer_id,
            order_id=validated.order_id,
            status="OPEN",
        )
        db.add(case)
        db.commit()

        return {
            "success": True,
            "case_id": case.id,
            "title": case.title,
            "case_type": case.case_type,
            "severity": case.severity,
            "status": case.status,
            "discrepancy_amount": float(case.discrepancy_amount),
        }
    finally:
        db.close()


@mcp.tool()
def add_evidence(
    case_id: str,
    evidence_type: str,
    source_table: str,
    source_id: str,
    content_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Attaches a deterministic evidence artifact to a case."""
    log_tool_call("add_evidence", case_id=case_id, evidence_type=evidence_type, source_table=source_table)
    AddEvidenceInput(
        case_id=case_id,
        evidence_type=evidence_type,
        source_table=source_table,
        source_id=source_id,
        content_payload=content_payload,
    )

    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {"success": False, "error": f"Case not found: {case_id}"}

        evidence = CaseEvidence(
            id=f"evi_{uuid.uuid4().hex[:8]}",
            case_id=case_id,
            evidence_type=evidence_type.upper(),
            source_table=source_table.lower(),
            source_id=source_id,
            content_payload=content_payload,
        )
        db.add(evidence)
        db.commit()

        return {
            "success": True,
            "evidence_id": evidence.id,
            "case_id": case_id,
            "evidence_type": evidence.evidence_type,
            "source_table": evidence.source_table,
        }
    finally:
        db.close()


@mcp.tool()
def get_case(case_id: str) -> Dict[str, Any]:
    """Retrieves full case details including attached evidence artifacts and pending actions."""
    log_tool_call("get_case", case_id=case_id)
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {"found": False, "error": f"Case not found: {case_id}"}

        evidence = db.query(CaseEvidence).filter(CaseEvidence.case_id == case_id).all()

        return {
            "found": True,
            "case": {
                "id": case.id,
                "title": case.title,
                "case_type": case.case_type,
                "severity": case.severity,
                "status": case.status,
                "headline": case.headline,
                "explanation": case.explanation,
                "discrepancy_amount": float(case.discrepancy_amount),
                "created_at": case.created_at.isoformat(),
                "customer_id": case.customer_id,
                "order_id": case.order_id,
                "evidence_items": [
                    {
                        "id": e.id,
                        "evidence_type": e.evidence_type,
                        "source_table": e.source_table,
                        "source_id": e.source_id,
                        "content_payload": e.content_payload,
                    }
                    for e in evidence
                ],
            },
        }
    finally:
        db.close()
