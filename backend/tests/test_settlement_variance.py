"""
Unit tests for Jarvis Deterministic Settlement Variance Service.
Tests math formulas, Decimal precision, classification states, and evidence generation.
"""

from decimal import Decimal
import pytest

from app.contracts.enums import SettlementVarianceStatus, Severity
from app.services.settlement_variance import (
    SettlementVarianceResult,
    calculate_settlement_variance,
)


def test_settlement_variance_fully_explained():
    """
    Test a settlement statement where gross minus all known deductions exactly matches bank credit.
    Expected variance: 0.00, Status: FULLY_EXPLAINED.
    """
    settlement_data = {
        "settlement_id": "STMT-TEST-001",
        "marketplace": "Meesho",
        "gross_order_value": "10000.00",
        "commission_fee": "1500.00",
        "shipping_fee": "800.00",
        "return_rto_fee": "200.00",
        "tax_deduction_tcs_tds": "100.00",
        "other_known_adjustment": "50.00",  # +50 subsidy
        "expected_net_payable": "7450.00",  # 10000 - (1500 + 800 + 200 + 100 - 50) = 7450.00
        "actual_bank_credit": "7450.00",
    }

    result = calculate_settlement_variance(settlement_data, correlation_id="test_corr_001")

    assert isinstance(result.expected_net_payable, Decimal)
    assert isinstance(result.variance_amount, Decimal)
    assert result.expected_net_payable == Decimal("7450.00")
    assert result.actual_bank_credit == Decimal("7450.00")
    assert result.variance_amount == Decimal("0.00")
    assert result.status == SettlementVarianceStatus.FULLY_EXPLAINED
    assert result.unexplained_residual == Decimal("0.00")
    assert not result.is_actionable
    assert len(result.findings) == 0


def test_settlement_variance_unexplained_residual():
    """
    Test the hero scenario: Meesho settlement with exact ₹1,550.00 unexplained residual variance.
    Expected variance: 1550.00, Status: UNEXPLAINED_RESIDUAL, Actionable: True.
    """
    settlement_data = {
        "settlement_id": "MEESHO-SETTLE-OCT2024",
        "marketplace": "Meesho",
        "gross_order_value": "52400.00",
        "commission_fee": "7860.00",
        "shipping_fee": "5200.00",
        "return_rto_fee": "2100.00",
        "tax_deduction_tcs_tds": "524.00",
        "other_known_adjustment": "350.00",  # packaging subsidy
        "expected_net_payable": "37066.00",
        "actual_bank_credit": "35516.00",
        "unexplained_deductions": [
            "1000.00 (Unitemized Quality Penalty Surcharge)",
            "550.00 (Unreconciled Logistics Weight Discrepancy)",
        ],
    }

    result = calculate_settlement_variance(settlement_data, correlation_id="test_corr_002")

    assert result.expected_net_payable == Decimal("37066.00")
    assert result.actual_bank_credit == Decimal("35516.00")
    assert result.variance_amount == Decimal("1550.00")
    assert result.status == SettlementVarianceStatus.UNEXPLAINED_RESIDUAL
    assert result.unexplained_residual == Decimal("1550.00")
    assert result.is_actionable is True

    # Validate findings and evidence
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.finding_type == "UNEXPLAINED_SETTLEMENT_RESIDUAL"
    assert finding.impact_amount == Decimal("1550.00")
    assert finding.severity == Severity.HIGH
    assert len(result.evidence_items) == 1
    assert result.evidence_items[0].source_entity_id == "MEESHO-SETTLE-OCT2024"


def test_settlement_variance_partially_explained_bonus():
    """
    Test settlement where actual credit exceeds expected net (e.g. promotional bonus or refund adjustment).
    Expected Status: PARTIALLY_EXPLAINED.
    """
    settlement_data = {
        "settlement_id": "STMT-BONUS-001",
        "marketplace": "Amazon",
        "gross_order_value": "20000.00",
        "commission_fee": "3000.00",
        "shipping_fee": "1000.00",
        "return_rto_fee": "0.00",
        "tax_deduction_tcs_tds": "200.00",
        "other_known_adjustment": "0.00",
        "expected_net_payable": "15800.00",
        "actual_bank_credit": "16300.00",  # +500 promotional incentive
    }

    result = calculate_settlement_variance(settlement_data, correlation_id="test_corr_003")

    assert result.variance_amount == Decimal("-500.00")
    assert result.status == SettlementVarianceStatus.PARTIALLY_EXPLAINED
    assert not result.is_actionable


def test_settlement_variance_insufficient_data():
    """
    Test corrupted/empty input with zero gross sales and zero credit.
    Expected Status: INSUFFICIENT_DATA.
    """
    settlement_data = {
        "settlement_id": "STMT-EMPTY",
        "marketplace": "Unknown",
        "gross_order_value": "0.00",
        "actual_bank_credit": "0.00",
    }

    result = calculate_settlement_variance(settlement_data, correlation_id="test_corr_004")

    assert result.status == SettlementVarianceStatus.INSUFFICIENT_DATA
    assert not result.is_actionable
    assert len(result.findings) == 0


def test_settlement_variance_strict_decimal_precision():
    """
    Test that floating point inaccuracies (e.g., 0.1 + 0.2 != 0.3 in IEEE 754)
    never occur in the deterministic settlement variance calculation.
    """
    settlement_data = {
        "settlement_id": "STMT-FLOAT-TEST",
        "marketplace": "Meesho",
        "gross_order_value": "100.10",
        "commission_fee": "10.20",
        "shipping_fee": "5.05",
        "return_rto_fee": "2.05",
        "tax_deduction_tcs_tds": "1.01",
        "other_known_adjustment": "0.00",
        # Expected Net: 100.10 - 10.20 - 5.05 - 2.05 - 1.01 = 81.79
        "expected_net_payable": "81.79",
        "actual_bank_credit": "80.00",
        # Variance: 81.79 - 80.00 = 1.79
    }

    result = calculate_settlement_variance(settlement_data, correlation_id="test_corr_005")

    assert result.expected_net_payable == Decimal("81.79")
    assert result.variance_amount == Decimal("1.79")
    assert str(result.variance_amount) == "1.79"  # Exact representation without floating tail
