import pytest
from decimal import Decimal
from datetime import date, datetime, timezone
from pydantic import ValidationError

from app.contracts import (
    # Enums
    CaseStatus,
    PaymentStatus,
    SettlementVarianceStatus,
    PromiseType,
    PromiseStatus,
    ActionType,
    ActionStatus,
    ApprovalStatus,
    EvidenceType,
    Severity,
    # Errors
    ErrorCode,
    ErrorDetail,
    JarvisContractException,
    # Models
    InboundEnvelope,
    NormalizedCommsContext,
    OrderRecord,
    InvoiceRecord,
    PaymentRecord,
    BankTransaction,
    SettlementLine,
    DeliveryRecord,
    PromiseRecord,
    EvidenceItem,
    CommercialCase,
    Finding,
    ActionProposal,
    PolicyDecision,
    ApprovalRequest,
    ApprovalDecision,
    DeliveryResult,
    PaymentLinkResult,
    ActionReceipt,
    RunResponse,
    ErrorResponse,
)


def test_contract_enums_values():
    assert CaseStatus.NEW == "new"
    assert CaseStatus.NEEDS_APPROVAL == "needs_approval"
    assert CaseStatus.BLOCKED == "blocked"
    assert PaymentStatus.PARTIALLY_PAID == "partially_paid"
    assert PaymentStatus.DUPLICATE_CANDIDATE == "duplicate_candidate"
    assert SettlementVarianceStatus.UNEXPLAINED_RESIDUAL == "unexplained_residual"
    assert PromiseType.FREE_GIFT == "free_gift"
    assert ActionType.RAZORPAY_PAYMENT_LINK == "razorpay_payment_link"
    assert Severity.CRITICAL == "critical"


def test_contract_error_codes():
    codes = [
        ErrorCode.FILE_PARSE_ERROR,
        ErrorCode.UNSUPPORTED_FILE_TYPE,
        ErrorCode.MISSING_REQUIRED_COLUMN,
        ErrorCode.AMBIGUOUS_PAYMENT_MATCH,
        ErrorCode.DUPLICATE_PAYMENT_CANDIDATE,
        ErrorCode.UNEXPLAINED_SETTLEMENT_VARIANCE,
        ErrorCode.MISSING_CONNECTED_ACCOUNT,
        ErrorCode.POLICY_BLOCKED,
        ErrorCode.APPROVAL_REQUIRED,
        ErrorCode.PROMPT_INJECTION_BLOCKED,
        ErrorCode.EXECUTION_FAILED,
        ErrorCode.LLM_OUTPUT_INVALID,
    ]
    assert len(codes) == 12


def test_order_record_strict_decimal_validation():
    # Valid model instantiation with Decimal
    order = OrderRecord(
        correlation_id="corr-101",
        order_number="ORD-2024-1001",
        channel="Instagram",
        customer_id="cust-01",
        order_date=date(2024, 10, 1),
        gross_amount=Decimal("1250.00"),
        discount_amount=Decimal("0.00"),
        net_amount=Decimal("1250.00"),
        status="PLACED",
    )
    assert order.gross_amount == Decimal("1250.00")
    assert isinstance(order.order_id, str)
    assert len(order.order_id) > 10

    # Strict validation: Float for Decimal must be rejected in strict mode
    with pytest.raises(ValidationError):
        OrderRecord(
            correlation_id="corr-102",
            order_number="ORD-2024-1002",
            channel="Instagram",
            customer_id="cust-01",
            order_date=date(2024, 10, 1),
            gross_amount=1250.00,  # float rejected!
            net_amount=Decimal("1250.00"),
            status="PLACED",
        )

    # Extra field forbidden
    with pytest.raises(ValidationError):
        OrderRecord(
            correlation_id="corr-103",
            order_number="ORD-2024-1003",
            channel="Instagram",
            customer_id="cust-01",
            order_date=date(2024, 10, 1),
            gross_amount=Decimal("1250.00"),
            net_amount=Decimal("1250.00"),
            status="PLACED",
            unauthorized_field="malicious",
        )


def test_promise_record_confidence_is_informational():
    promise = PromiseRecord(
        correlation_id="corr-201",
        customer_id="cust-02",
        speaker="SELLER",
        promise_type=PromiseType.FREE_GIFT,
        promise_details="Complimentary silk scrunchie",
        raw_message_snippet="I will add a free silk scrunchie 🎁",
        confidence_score=Decimal("0.95"),
    )
    assert promise.confidence_score == Decimal("0.95")
    assert promise.status == PromiseStatus.PENDING


def test_action_receipt_and_chaining():
    receipt = ActionReceipt(
        correlation_id="corr-301",
        approval_id="appr-101",
        action_id="act-101",
        case_id="case-101",
        decision=ApprovalStatus.APPROVED,
        actor="Seller (Manual HITL)",
        payload_snapshot={"amount": "450.00", "recipient": "+91 98*****789"},
        execution_result={"short_url": "https://rzp.io/i/test_xyz"},
        receipt_hash="a" * 64,
        tamper_chain_previous_hash="0" * 64,
    )
    assert receipt.decision == ApprovalStatus.APPROVED
    assert len(receipt.receipt_hash) == 64
