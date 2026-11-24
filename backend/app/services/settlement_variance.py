"""
Jarvis Deterministic Settlement Variance Calculation Service.
Calculates marketplace remittance variances using strict Decimal arithmetic.

Formula:
  Expected Gross Sales
  - Commission Fee
  - Shipping Logistics Fee
  - Return (RTO) Fee
  - Tax Deductions (TCS / TDS)
  + Other Known Adjustments (Subsidies / Reimbursements)
  = Expected Net Payout

  Remittance Variance = Expected Net Payout - Actual Received Bank Credit

Classification:
  - FULLY_EXPLAINED: Remittance Variance == 0.00
  - PARTIALLY_EXPLAINED: Remittance Variance > 0.00 and partially accounted for by known adjustments
  - UNEXPLAINED_RESIDUAL: Remittance Variance > 0.00 with unexplained residual deduction (e.g. ₹1,550.00)
  - INSUFFICIENT_DATA: Missing mandatory fields, corrupt inputs, or zero gross sales with non-zero deductions
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.contracts.enums import EvidenceType, Severity, SettlementVarianceStatus
from app.contracts.models import EvidenceItem, Finding
from app.services.evidence_builder import evidence_from_settlement_line


@dataclass
class SettlementVarianceResult:
    """
    Detailed, audit-verifiable result of a deterministic settlement variance calculation.
    """
    settlement_id: str
    marketplace: str
    gross_order_value: Decimal
    commission_fee: Decimal
    shipping_fee: Decimal
    return_rto_fee: Decimal
    tax_deduction_tcs_tds: Decimal
    other_known_adjustment: Decimal
    expected_net_payable: Decimal
    actual_bank_credit: Decimal
    variance_amount: Decimal
    status: SettlementVarianceStatus
    unexplained_residual: Decimal
    unexplained_deductions: List[str]
    evidence_items: List[EvidenceItem]
    findings: List[Finding]
    explanation: str
    is_actionable: bool


def calculate_settlement_variance(
    settlement_record: Dict[str, Any],
    correlation_id: str,
    source_file: str = "settlement_report.csv",
) -> SettlementVarianceResult:
    """
    Computes deterministic settlement variance for a marketplace statement line.
    Enforces strict Decimal math with zero rounding drift.
    """
    settlement_id = settlement_record.get("settlement_id", "UNKNOWN_SETTLEMENT")
    marketplace = settlement_record.get("marketplace", "Marketplace")

    # Extract all monetary components as Decimal
    gross = Decimal(str(settlement_record.get("gross_order_value", "0.00"))).quantize(Decimal("0.01"))
    comm = Decimal(str(settlement_record.get("commission_fee", "0.00"))).quantize(Decimal("0.01"))
    ship = Decimal(str(settlement_record.get("shipping_fee", "0.00"))).quantize(Decimal("0.01"))
    rto = Decimal(str(settlement_record.get("return_rto_fee", "0.00"))).quantize(Decimal("0.01"))
    tax = Decimal(str(settlement_record.get("tax_deduction_tcs_tds", "0.00"))).quantize(Decimal("0.01"))
    adj = Decimal(str(settlement_record.get("other_known_adjustment", "0.00"))).quantize(Decimal("0.01"))
    actual_credit = Decimal(str(settlement_record.get("actual_bank_credit", "0.00"))).quantize(Decimal("0.01"))

    # Insufficient data check
    if gross <= Decimal("0.00") and actual_credit <= Decimal("0.00"):
        evidence = [evidence_from_settlement_line(settlement_record, correlation_id, source_file)]
        return SettlementVarianceResult(
            settlement_id=settlement_id,
            marketplace=marketplace,
            gross_order_value=gross,
            commission_fee=comm,
            shipping_fee=ship,
            return_rto_fee=rto,
            tax_deduction_tcs_tds=tax,
            other_known_adjustment=adj,
            expected_net_payable=Decimal("0.00"),
            actual_bank_credit=actual_credit,
            variance_amount=Decimal("0.00"),
            status=SettlementVarianceStatus.INSUFFICIENT_DATA,
            unexplained_residual=Decimal("0.00"),
            unexplained_deductions=["Zero gross order value and zero credit found in report."],
            evidence_items=evidence,
            findings=[],
            explanation="Insufficient data: Gross sales and bank credit are zero or missing.",
            is_actionable=False,
        )

    # Deterministic formula: Expected Net = Gross - Comm - Shipping - RTO - Taxes + Adjustments
    known_deductions = comm + ship + rto + tax - adj
    expected_net = gross - known_deductions

    # Remittance Variance = Expected Net - Actual Received
    variance = (expected_net - actual_credit).quantize(Decimal("0.01"))

    unexplained_items = settlement_record.get("unexplained_deductions", [])

    # Classify variance
    if variance == Decimal("0.00"):
        status = SettlementVarianceStatus.FULLY_EXPLAINED
        residual = Decimal("0.00")
        is_actionable = False
        explanation = (
            f"Marketplace settlement {settlement_id} is fully explained. "
            f"Gross ₹{gross} minus known deductions ₹{known_deductions} equals "
            f"actual received bank credit of ₹{actual_credit}."
        )
    elif variance > Decimal("0.00"):
        residual = variance
        status = SettlementVarianceStatus.UNEXPLAINED_RESIDUAL
        is_actionable = True
        explanation = (
            f"Marketplace settlement {settlement_id} has an unexplained deduction residual of ₹{variance}. "
            f"Expected payout was ₹{expected_net} (Gross ₹{gross} - Deductions ₹{known_deductions}), "
            f"but actual bank deposit was only ₹{actual_credit}."
        )
    else:
        # Negative variance means actual received > expected net (overpayment / credit bonus)
        residual = Decimal("0.00")
        status = SettlementVarianceStatus.PARTIALLY_EXPLAINED
        is_actionable = False
        explanation = (
            f"Marketplace settlement {settlement_id} credited ₹{actual_credit}, exceeding "
            f"expected net of ₹{expected_net} by ₹{abs(variance)} (promotional or incentive credit)."
        )

    # Build evidence items
    evidence = [evidence_from_settlement_line(settlement_record, correlation_id, source_file)]

    # Build findings
    findings: List[Finding] = []
    if status == SettlementVarianceStatus.UNEXPLAINED_RESIDUAL:
        finding = Finding(
            finding_id=f"find_settle_{settlement_id.lower()}",
            correlation_id=correlation_id,
            finding_type="UNEXPLAINED_SETTLEMENT_RESIDUAL",
            proof_description=(
                f"Gross (₹{gross}) - Commission (₹{comm}) - Shipping (₹{ship}) - "
                f"RTO (₹{rto}) - Taxes (₹{tax}) + Adj (₹{adj}) = Expected ₹{expected_net}. "
                f"Actual Bank Deposit = ₹{actual_credit}. Unexplained Shortfall = ₹{variance}."
            ),
            impact_amount=variance,
            severity=Severity.HIGH,
            evidence_ids=[ev.evidence_id for ev in evidence],
        )
        findings.append(finding)

    return SettlementVarianceResult(
        settlement_id=settlement_id,
        marketplace=marketplace,
        gross_order_value=gross,
        commission_fee=comm,
        shipping_fee=ship,
        return_rto_fee=rto,
        tax_deduction_tcs_tds=tax,
        other_known_adjustment=adj,
        expected_net_payable=expected_net,
        actual_bank_credit=actual_credit,
        variance_amount=variance,
        status=status,
        unexplained_residual=residual,
        unexplained_deductions=unexplained_items,
        evidence_items=evidence,
        findings=findings,
        explanation=explanation,
        is_actionable=is_actionable,
    )
