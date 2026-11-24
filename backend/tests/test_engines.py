import pytest
from decimal import Decimal
from app.database import SessionLocal, engine, Base
from app.seed.generator import generate_synthetic_data
from app.engines.reconciler import ReconciliationEngine
from app.engines.variance import VarianceEngine


@pytest.fixture(scope="module")
def db_session():
    generate_synthetic_data()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_deterministic_reconciliation(db_session):
    engine = ReconciliationEngine(db_session)
    result = engine.run_reconciliation()

    # Verify that partials are accurately detected (exactly 3)
    assert result["partial_count"] == 3
    shortfalls = sorted([p["shortfall_amount"] for p in result["partials"]])
    assert shortfalls == [400.0, 450.0, 500.0]

    # Verify that duplicate candidates are detected (exactly 2)
    assert result["duplicate_candidates_count"] == 2
    duplicate_amounts = sorted([d["duplicate_amount"] for d in result["duplicates"]])
    assert duplicate_amounts == [899.0, 1250.0]

    # Verify total transactions accounted for
    assert result["total_transactions"] == 50
    assert result["unmatched_count"] == 3


def test_deterministic_settlement_variance(db_session):
    engine = VarianceEngine(db_session)
    results = engine.analyze_all_settlements()

    assert len(results) == 1
    meesho = results[0]

    assert meesho["marketplace"] == "Meesho"
    assert meesho["gross_order_value"] == 48500.0
    assert meesho["total_known_deductions"] == 14035.0  # 7250 + 4800 + 1500 + 485
    assert meesho["calculated_expected_payout"] == 34465.0
    assert meesho["actual_bank_credit"] == 33615.0
    assert meesho["unexplained_residual"] == 850.0
    assert meesho["has_unexplained_variance"] is True
