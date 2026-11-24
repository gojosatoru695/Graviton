from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ChannelEnum(str, Enum):
    INSTAGRAM = "Instagram"
    WHATSAPP = "WhatsApp"
    WEBSITE = "Website"
    MEESHO = "Meesho"


class OrderStatusEnum(str, Enum):
    PLACED = "PLACED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class ReconciliationStatusEnum(str, Enum):
    MATCHED = "MATCHED"
    PARTIAL = "PARTIAL"
    UNMATCHED = "UNMATCHED"
    DUPLICATE_CANDIDATE = "DUPLICATE_CANDIDATE"


class PromiseTypeEnum(str, Enum):
    DELIVERY_DATE = "DELIVERY_DATE"
    FREE_GIFT = "FREE_GIFT"
    DISCOUNT = "DISCOUNT"
    CUSTOMIZATION = "CUSTOMIZATION"
    PAYMENT_COMMITMENT = "PAYMENT_COMMITMENT"


class PromiseStatusEnum(str, Enum):
    PENDING = "PENDING"
    KEPT = "KEPT"
    BROKEN = "BROKEN"
    UNRECORDED = "UNRECORDED"


class CaseTypeEnum(str, Enum):
    PAYMENT_SHORTFALL = "PAYMENT_SHORTFALL"
    DUPLICATE_PAYMENT = "DUPLICATE_PAYMENT"
    MARKETPLACE_VARIANCE = "MARKETPLACE_VARIANCE"
    BROKEN_PROMISE = "BROKEN_PROMISE"
    UNRECORDED_GIFT = "UNRECORDED_GIFT"


class CaseSeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ActionTypeEnum(str, Enum):
    RAZORPAY_PAYMENT_LINK = "RAZORPAY_PAYMENT_LINK"
    GMAIL_DRAFT = "GMAIL_DRAFT"
    SETTLEMENT_DISPUTE_PACK = "SETTLEMENT_DISPUTE_PACK"


class ActionDecisionEnum(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DRAFT = "DRAFT"


class CustomerSchema(BaseModel):
    id: str
    name: str
    phone: str
    instagram_handle: Optional[str] = None
    email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrderSchema(BaseModel):
    id: str
    customer_id: str
    order_number: str
    channel: str
    order_date: date
    gross_amount: float
    discount_amount: float = 0.0
    net_amount: float
    status: str
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None
    customer_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BankTransactionSchema(BaseModel):
    id: str
    transaction_date: date
    transaction_type: str
    amount: float
    utr_reference: str
    sender_name: Optional[str] = None
    sender_upi_id: Optional[str] = None
    raw_description: str
    matched_order_id: Optional[str] = None
    reconciliation_status: str

    model_config = ConfigDict(from_attributes=True)


class SettlementWaterfallSchema(BaseModel):
    settlement_id: str
    marketplace: str
    period_start: date
    period_end: date
    gross_order_value: float
    commission_fee: float
    logistics_fee: float
    return_penalties: float
    taxes_tcs_tds: float
    calculated_expected_payout: float
    actual_bank_credit: float
    unexplained_residual: float
    bank_utr: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ExtractedPromiseSchema(BaseModel):
    speaker: str
    promise_type: PromiseTypeEnum
    promise_details: str
    target_date: Optional[date] = None
    raw_snippet: str
    confidence_score: float

    @field_validator("confidence_score")
    def clamp_score(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class PromiseSchema(BaseModel):
    id: str
    customer_id: str
    order_id: Optional[str] = None
    customer_name: Optional[str] = None
    order_number: Optional[str] = None
    channel: str
    timestamp: datetime
    speaker: str
    promise_type: str
    promise_details: str
    target_date: Optional[date] = None
    status: str
    raw_message_snippet: str
    confidence_score: float

    model_config = ConfigDict(from_attributes=True)


class CaseEvidenceSchema(BaseModel):
    id: str
    case_id: str
    evidence_type: str
    source_table: str
    source_id: str
    content_payload: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class PendingActionSchema(BaseModel):
    id: str
    case_id: str
    action_type: str
    target_recipient: str
    action_summary: str
    payload: Dict[str, Any]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActionReceiptSchema(BaseModel):
    id: str
    pending_action_id: str
    case_id: str
    decision: str
    actor: str
    timestamp: datetime
    payload_snapshot: Dict[str, Any]
    execution_result: Dict[str, Any]
    receipt_hash: str
    tamper_chain_previous_hash: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CaseDetailSchema(BaseModel):
    id: str
    title: str
    case_type: str
    severity: str
    status: str
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    order_id: Optional[str] = None
    order_number: Optional[str] = None
    discrepancy_amount: float
    headline: str
    explanation: str
    created_at: datetime
    evidence_items: List[CaseEvidenceSchema] = []
    pending_actions: List[PendingActionSchema] = []
    receipts: List[ActionReceiptSchema] = []

    model_config = ConfigDict(from_attributes=True)


class ActionDecisionRequest(BaseModel):
    decision: ActionDecisionEnum
    rejection_reason: Optional[str] = None


class AskJarvisRequest(BaseModel):
    query: str


class AskJarvisResponse(BaseModel):
    answer: str
    grounded_evidence_ids: List[str] = []
    is_safe: bool = True
    flagged_injection_reason: Optional[str] = None
