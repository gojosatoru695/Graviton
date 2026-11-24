"""
Pydantic Schemas for Jarvis AI Services:
- Structured Promise Extraction
- Message Safety Classification & Prompt Injection Defense
- Safe Seller Communication Draft Generation
"""

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PromiseType(str, Enum):
    """
    Standardized categories of commercial promises extracted from communications.
    """
    DELIVERY_DEADLINE = "delivery_deadline"
    REFUND_PROMISE = "refund_promise"
    REPLACEMENT_PROMISE = "replacement_promise"
    DISCOUNT_PROMISE = "discount_promise"
    FREE_GIFT_PROMISE = "free_gift_promise"
    PAYMENT_PROMISE = "payment_promise"
    CUSTOM_ORDER_PROMISE = "custom_order_promise"
    FOLLOW_UP_PROMISE = "follow_up_promise"


class RiskLevel(str, Enum):
    """
    Financial and reputation risk rating of an extracted commitment.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MessageClassification(str, Enum):
    """
    Operational classification of incoming text messages.
    """
    BENIGN_CUSTOMER_MESSAGE = "benign_customer_message"
    PROMPT_INJECTION_ATTEMPT = "prompt_injection_attempt"
    SUPPORT_INQUIRY = "support_inquiry"
    COMPLAINT = "complaint"
    PAYMENT_NOTIFICATION = "payment_notification"


class OrderRefConfidence(str, Enum):
    """
    Certainty level linking a message to an explicit order reference.
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class ExtractedPromise(BaseModel):
    """
    Individual verifiable commitment extracted from conversation text.
    """
    model_config = ConfigDict(strict=False, extra="forbid")

    promise_type: PromiseType = Field(
        ...,
        description="Categorical type of commercial promise."
    )
    promisor: str = Field(
        ...,
        description="Party making the commitment ('SELLER' or 'CUSTOMER' or named speaker)."
    )
    promisee: str = Field(
        ...,
        description="Party to whom the commitment was made ('CUSTOMER' or 'SELLER')."
    )
    deadline: Optional[str] = Field(
        None,
        description="Resolved calendar date or deadline (YYYY-MM-DD)."
    )
    amount: Optional[Decimal] = Field(
        None,
        description="Monetary amount involved in the promise in INR (strictly Decimal)."
    )
    order_reference: Optional[str] = Field(
        None,
        description="Exact order identifier (e.g. 'ORD-2024-1005') if cited."
    )
    order_ref_confidence: OrderRefConfidence = Field(
        default=OrderRefConfidence.NONE,
        description="Confidence level of order reference attribution."
    )
    conditions: List[str] = Field(
        default_factory=list,
        description="Prerequisites or contingencies attached to the promise."
    )
    confidence: Decimal = Field(
        default=Decimal("0.90"),
        ge=Decimal("0.00"),
        le=Decimal("1.00"),
        description="Extraction certainty score."
    )
    source: str = Field(
        ...,
        description="Origin channel ('WhatsApp' or 'Gmail')."
    )
    exact_source_span: str = Field(
        ...,
        description="Verbatim substring excerpt from the raw message containing the promise."
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.LOW,
        description="Operational risk rating of this commitment."
    )
    raw_summary: str = Field(
        ...,
        description="Plain-English summary of the commitment."
    )


class PromiseExtractionResult(BaseModel):
    """
    Complete structured extraction payload returned by the PromiseExtractor.
    """
    model_config = ConfigDict(strict=False, extra="forbid")

    correlation_id: str = Field(
        ...,
        description="Trace identifier for the extraction run."
    )
    customer_name: Optional[str] = Field(
        None,
        description="Customer name or handle associated with the conversation."
    )
    current_date: str = Field(
        ...,
        description="Base reference date used for relative date resolution (YYYY-MM-DD)."
    )
    is_prompt_injection: bool = Field(
        default=False,
        description="Flag indicating message contained adversarial jailbreak or prompt injection."
    )
    injection_reason: Optional[str] = Field(
        None,
        description="Explanation if an injection attempt was detected and neutralized."
    )
    promises: List[ExtractedPromise] = Field(
        default_factory=list,
        description="List of verified commitments extracted from the text."
    )
    unresolved_commitments: List[str] = Field(
        default_factory=list,
        description="Ambiguous remarks that could not be reliably classified as promises."
    )


class MessageClassificationResult(BaseModel):
    """
    Result of safety and intent evaluation on an inbound message.
    """
    model_config = ConfigDict(strict=False, extra="forbid")

    classification: MessageClassification = Field(
        ...,
        description="Primary intent classification."
    )
    is_safe: bool = Field(
        ...,
        description="True if message is safe to process; False if injection/attack detected."
    )
    threat_indicators: List[str] = Field(
        default_factory=list,
        description="Specific jailbreak patterns or suspicious phrases detected."
    )
    sanitized_intent: str = Field(
        ...,
        description="Safe summary of customer intent with instructions stripped."
    )


class DraftRequest(BaseModel):
    """
    Specification for generating a safe outbound communication draft.
    """
    model_config = ConfigDict(strict=False, extra="forbid")

    case_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual metadata regarding the discrepancy case."
    )
    finding: Optional[Dict[str, Any]] = Field(
        None,
        description="Verified deterministic finding backing the communication."
    )
    customer_tone: str = Field(
        default="polite",
        description="Tone of customer in previous communications ('polite', 'urgent', 'frustrated', 'neutral')."
    )
    desired_action: str = Field(
        ...,
        description="Action type ('payment_reminder', 'delay_apology', 'clarification', 'gift_confirmation')."
    )
    customer_name: str = Field(
        ...,
        description="Customer salutation name."
    )
    order_reference: Optional[str] = Field(
        None,
        description="Associated order reference code."
    )
    payment_link_url: Optional[str] = Field(
        None,
        description="Simulated or test Razorpay payment link URL if payment is requested."
    )
    shortfall_amount: Optional[Decimal] = Field(
        None,
        description="Outstanding balance shortfall if requesting payment."
    )


class SafeDraftResponse(BaseModel):
    """
    Validated seller draft ready for human approval.
    """
    model_config = ConfigDict(strict=False, extra="forbid")

    subject: str = Field(
        ...,
        description="Email subject line or WhatsApp message title."
    )
    body: str = Field(
        ...,
        description="Draft message body formatted for Indian small-business seller."
    )
    payment_link_placeholder: Optional[str] = Field(
        None,
        description="Placeholder token for payment link (e.g. '{{payment_link}}')."
    )
    confidence: Decimal = Field(
        default=Decimal("0.95"),
        description="Confidence score of draft alignment with verified facts."
    )
    safety_flags: List[str] = Field(
        default_factory=list,
        description="Safety audit notes (e.g. 'No unverified refund promised')."
    )
    is_approved_by_policy: bool = Field(
        default=True,
        description="Whether draft complies with seller communication safety policy."
    )
