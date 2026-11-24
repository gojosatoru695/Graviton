import pytest
import hashlib
import json
from app.database import SessionLocal
from app.seed.generator import generate_synthetic_data
from app.engines.synthesizer import CaseSynthesizer
from app.models.cases import PendingAction, ActionReceipt
from app.services.receipt_service import ReceiptService


@pytest.fixture(scope="module")
def db_session():
    generate_synthetic_data()
    db = SessionLocal()
    synth = CaseSynthesizer(db)
    synth.synthesize_all_cases()
    try:
        yield db
    finally:
        db.close()


def test_action_approval_creates_receipt_and_chain(db_session):
    service = ReceiptService(db_session)
    action = db_session.query(PendingAction).filter(
        PendingAction.action_type == "RAZORPAY_PAYMENT_LINK",
        PendingAction.status == "PENDING"
    ).first()

    assert action is not None

    # Approve action
    res = service.process_decision(
        action_id=action.id,
        decision="APPROVED",
        actor="Seller (Manual HITL)"
    )

    assert res["decision"] == "APPROVED"
    assert "receipt_hash" in res
    assert res["execution_result"]["mode"] == "TEST_SANDBOX"
    assert "https://rzp.io/i/test_" in res["execution_result"]["short_url"]

    # Verify receipt saved in DB
    receipt = db_session.query(ActionReceipt).filter(ActionReceipt.id == res["receipt_id"]).first()
    assert receipt is not None
    assert receipt.receipt_hash == res["receipt_hash"]


def test_action_rejection_creates_audit_receipt(db_session):
    service = ReceiptService(db_session)
    action = db_session.query(PendingAction).filter(
        PendingAction.action_type == "GMAIL_DRAFT",
        PendingAction.status == "PENDING"
    ).first()

    assert action is not None

    res = service.process_decision(
        action_id=action.id,
        decision="REJECTED",
        actor="Seller (Manual HITL)",
        rejection_reason="Customer already contacted via phone"
    )

    assert res["decision"] == "REJECTED"
    assert res["execution_result"]["status"] == "ACTION_REJECTED_BY_USER"

    receipt = db_session.query(ActionReceipt).filter(ActionReceipt.id == res["receipt_id"]).first()
    assert receipt is not None
    assert receipt.decision == "REJECTED"
