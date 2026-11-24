import pytest
from app.database import SessionLocal
from app.seed.generator import generate_synthetic_data
from app.engines.synthesizer import CaseSynthesizer
from app.models.cases import Case, CaseEvidence, PendingAction


@pytest.fixture(scope="module")
def db_session():
    generate_synthetic_data()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_case_synthesizer_generates_all_expected_cases(db_session):
    synth = CaseSynthesizer(db_session)
    cases = synth.synthesize_all_cases()

    # Verify cases were created
    all_cases = db_session.query(Case).all()
    assert len(all_cases) >= 8

    # Verify specific case types
    case_types = [c.case_type for c in all_cases]
    assert "PAYMENT_SHORTFALL" in case_types
    assert "DUPLICATE_PAYMENT" in case_types
    assert "MARKETPLACE_VARIANCE" in case_types
    assert "BROKEN_PROMISE" in case_types
    assert "UNRECORDED_GIFT" in case_types

    # Verify evidence items attached
    evidence_count = db_session.query(CaseEvidence).count()
    assert evidence_count >= 10

    # Verify pending actions generated with PENDING status (zero automatic execution)
    pending_actions = db_session.query(PendingAction).all()
    assert len(pending_actions) >= 8
    for a in pending_actions:
        assert a.status == "PENDING"
