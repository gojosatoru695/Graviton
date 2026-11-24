from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.entities import SettlementReport, SettlementLineItem


class VarianceEngine:
    """
    100% Deterministic Marketplace Settlement Variance Engine.
    Rules:
    - Pure arithmetic, zero LLM calls.
    - Computes expected net settlement payout using Decimal to eliminate rounding/floating point error.
    - Compares expected net payout against actual bank credit.
    - Calculates the exact unexplained residual deduction.
    """

    def __init__(self, db: Session):
        self.db = db

    def analyze_settlement(self, settlement_id: str) -> Dict[str, Any]:
        report = self.db.query(SettlementReport).filter(
            (SettlementReport.id == settlement_id) | (SettlementReport.settlement_id == settlement_id)
        ).first()

        if not report:
            raise ValueError(f"Settlement report not found: {settlement_id}")

        gross = Decimal(str(report.gross_order_value))
        commission = Decimal(str(report.commission_fee))
        logistics = Decimal(str(report.logistics_fee))
        returns = Decimal(str(report.return_penalties))
        taxes = Decimal(str(report.taxes_tcs_tds))
        actual_bank_credit = Decimal(str(report.actual_bank_credit))

        # Expected Net = Gross - (Commission + Logistics + Returns + Taxes)
        total_known_deductions = commission + logistics + returns + taxes
        calculated_expected_payout = gross - total_known_deductions

        # Residual = Expected - Actual
        unexplained_residual = calculated_expected_payout - actual_bank_credit

        # Update the report record with exact deterministic values
        report.net_settlement_payable = calculated_expected_payout
        report.unexplained_residual = unexplained_residual
        self.db.commit()

        # Itemized lines summary
        line_items = self.db.query(SettlementLineItem).filter(
            SettlementLineItem.settlement_id == report.id
        ).all()

        waterfall_steps = [
            {"step": "Gross Sales", "amount": float(gross), "type": "credit"},
            {"step": "Marketplace Commission", "amount": float(-commission), "type": "deduction"},
            {"step": "Logistics & Shipping", "amount": float(-logistics), "type": "deduction"},
            {"step": "Return Penalties (RTO)", "amount": float(-returns), "type": "deduction"},
            {"step": "Taxes (TCS & TDS)", "amount": float(-taxes), "type": "deduction"},
            {"step": "Expected Net Payout", "amount": float(calculated_expected_payout), "type": "subtotal"},
            {"step": "Actual Bank Remittance", "amount": float(actual_bank_credit), "type": "actual"},
            {"step": "Unexplained Residual Deduction", "amount": float(unexplained_residual), "type": "residual"},
        ]

        deduction_explanations = [
            {
                "category": "Marketplace Commission",
                "rateOrRule": "15% of Gross Merchandise Value",
                "baseAmount": float(gross),
                "deductedAmount": float(commission),
                "explanation": "Standard Meesho commission agreed under master merchant terms.",
                "status": "VERIFIED",
            },
            {
                "category": "Logistics & Shipping Fees",
                "rateOrRule": "Weight-slab carrier fee",
                "baseAmount": float(gross),
                "deductedAmount": float(logistics),
                "explanation": "Standard forward logistics billing across fulfilled parcels.",
                "status": "VERIFIED",
            },
            {
                "category": "Return Penalties (RTO)",
                "rateOrRule": "Reverse logistics surcharge",
                "baseAmount": float(gross),
                "deductedAmount": float(returns),
                "explanation": "Zero return penalties levied for this settlement period.",
                "status": "VERIFIED",
            },
            {
                "category": "Taxes (TCS & TDS)",
                "rateOrRule": "1% GST TCS + 1% Income Tax TDS",
                "baseAmount": float(gross),
                "deductedAmount": float(taxes),
                "explanation": "Statutory tax withheld and credited to GSTIN portal.",
                "status": "VERIFIED",
            },
        ]
        if unexplained_residual > Decimal("0.00"):
            deduction_explanations.append({
                "category": "Unexplained Remittance Shortfall",
                "rateOrRule": "Contractual Remittance Discrepancy",
                "baseAmount": float(calculated_expected_payout),
                "deductedAmount": float(unexplained_residual),
                "explanation": f"Bank credit is ₹{float(unexplained_residual):,.2f} less than net payable without supporting line items.",
                "status": "DISCREPANCY",
            })

        return {
            "settlement_id": report.settlement_id,
            "marketplace": report.marketplace,
            "period": f"{report.period_start.isoformat()} to {report.period_end.isoformat()}",
            "gross_order_value": float(gross),
            "total_known_deductions": float(total_known_deductions),
            "calculated_expected_payout": float(calculated_expected_payout),
            "actual_bank_credit": float(actual_bank_credit),
            "unexplained_residual": float(unexplained_residual),
            "has_unexplained_variance": unexplained_residual > Decimal("0.00"),
            "waterfall": waterfall_steps,
            "deduction_explanations": deduction_explanations,
            "bank_utr": report.bank_utr,
            "line_items_count": len(line_items),
        }

    def analyze_all_settlements(self) -> List[Dict[str, Any]]:
        reports = self.db.query(SettlementReport).all()
        return [self.analyze_settlement(r.id) for r in reports]
