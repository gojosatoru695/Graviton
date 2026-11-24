from datetime import date, datetime, timezone
from decimal import Decimal
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import (
    ActionStatus,
    ActionType,
    ApprovalStatus,
    CaseStatus,
    EvidenceType,
    PaymentStatus,
    PromiseStatus,
    PromiseType,
    SettlementVarianceStatus,
    Severity,
)
from app.contracts.errors import ErrorCode, ErrorDetail


def generate_uuid() -> str:
    """Generate a stable, lowercase UUID4 string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Generate a timezone-aware UTC datetime formatted to ISO 8601."""
    return datetime.now(timezone.utc)


class ContractBaseModel(BaseModel):
    """
    Base model establishing strict validation, immutable boundaries,
    and ISO 8601 serialization across all Jarvis contracts.
    """
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        validate_default=True,
        use_enum_values=True,
        ser_json_timedelta="iso8601",
    )


# ---------------------------------------------------------------------------
# Ingestion & Context Models
# ---------------------------------------------------------------------------

class InboundEnvelope(ContractBaseModel):
    """
    Envelope wrapping all raw ingested customer files, webhooks, or API payloads.
    Provides immutable provenance and trace correlation.
    """
    envelope_id: str = Field(
        default_factory=generate_uuid,
        description="Globally unique stable identifier for the inbound ingestion envelope."
    )
    correlation_id: str = Field(
        default_factory=generate_uuid,
        description="Distributed tracing identifier propagated across all downstream pipeline stages."
    )
    source_filename: str = Field(
        ...,
        description="Name of the uploaded source file (e.g. 'orders.csv', 'whatsapp_export.txt')."
    )
    source_channel: str = Field(
        ...,
        description="Ingestion origin channel (e.g. 'MANUAL_UPLOAD', 'WHATSAPP_EXPORT', 'BANK_CSV')."
    )
    mime_type: str = Field(
        ...,
        description="Validated MIME type of the ingested payload."
    )
    file_size_bytes: int = Field(
        ...,
        ge=1,
        description="Payload size in bytes."
    )
    checksum_sha256: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="Cryptographic SHA-256 hash of the raw input bytes for integrity verification."
    )
    ingested_at: datetime = Field(
        default_factory=utc_now,
        description="Time of ingestion in UTC ISO 8601 format."
    )
    raw_payload: Optional[str] = Field(
        None,
        description="Text representation of ingested file or reference URI. Null if file stored in object storage."
    )


class NormalizedCommsContext(ContractBaseModel):
    """
    Normalized conversation context extracted from WhatsApp, Instagram, or social DMs.
    """
    context_id: str = Field(
        default_factory=generate_uuid,
        description="Stable unique identifier for the communication message or turn."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier linking this communication turn to the ingestion envelope."
    )
    channel: str = Field(
        ...,
        description="Communication channel (e.g., 'WhatsApp', 'Instagram_DM', 'Website_Chat')."
    )
    message_timestamp: datetime = Field(
        ...,
        description="Timestamp recorded in the conversation export in UTC ISO 8601."
    )
    speaker_role: str = Field(
        ...,
        description="Role of the message author: 'SELLER', 'CUSTOMER', or 'SYSTEM'."
    )
    speaker_identifier: str = Field(
        ...,
        description="Customer or seller phone, handle, or identifier (e.g. '@priya_sharma_delhi')."
    )
    raw_text: str = Field(
        ...,
        description="Verbatim message content treated strictly as untrusted data."
    )
    is_quarantined: bool = Field(
        default=False,
        description="Whether this message matched adversarial or prompt-injection firewall patterns."
    )
    quarantine_reason: Optional[str] = Field(
        None,
        description="Explanation if input was quarantined by safety firewall."
    )


# ---------------------------------------------------------------------------
# Core Domain Records
# ---------------------------------------------------------------------------

class OrderRecord(ContractBaseModel):
    """
    Normalized customer order placed across any sales channel.
    """
    order_id: str = Field(
        default_factory=generate_uuid,
        description="Stable internal UUID for the order."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier linking the order to its ingestion run."
    )
    order_number: str = Field(
        ...,
        description="Seller's public business order identifier (e.g. 'ORD-2024-1014')."
    )
    channel: str = Field(
        ...,
        description="Order acquisition channel ('Instagram', 'WhatsApp', 'Website', 'Meesho')."
    )
    customer_id: str = Field(
        ...,
        description="Stable identifier for the associated customer profile."
    )
    order_date: date = Field(
        ...,
        description="Calendar date the order was created (YYYY-MM-DD)."
    )
    gross_amount: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Order gross price before discounts in INR (strictly Decimal)."
    )
    discount_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Discounts applied to the order in INR."
    )
    net_amount: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Total expected payable balance in INR (gross_amount - discount_amount)."
    )
    currency: str = Field(
        default="INR",
        min_length=3,
        max_length=3,
        description="Three-letter ISO 4217 currency code (default: INR)."
    )
    status: str = Field(
        ...,
        description="Order fulfillment status ('PLACED', 'SHIPPED', 'DELIVERED', 'CANCELLED')."
    )
    expected_delivery_date: Optional[date] = Field(
        None,
        description="Promised or scheduled delivery date if available."
    )
    actual_delivery_date: Optional[date] = Field(
        None,
        description="Actual delivery date confirmed by logistics tracking."
    )
    tracking_number: Optional[str] = Field(
        None,
        description="Airway bill (AWB) or courier tracking reference."
    )
    notes: Optional[str] = Field(
        None,
        description="Fulfillment instructions or item descriptions."
    )


class InvoiceRecord(ContractBaseModel):
    """
    Commercial tax invoice linked to an order.
    """
    invoice_id: str = Field(
        default_factory=generate_uuid,
        description="Stable unique identifier for the tax invoice."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier linking invoice to its creation or ingestion run."
    )
    order_id: str = Field(
        ...,
        description="Foreign reference to the corresponding OrderRecord.order_id."
    )
    invoice_number: str = Field(
        ...,
        description="Legal sequential tax invoice number (e.g. 'INV-2024-201')."
    )
    invoice_date: date = Field(
        ...,
        description="Invoice date of issue (YYYY-MM-DD)."
    )
    subtotal: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Taxable base value before GST in INR (strictly Decimal)."
    )
    tax_amount: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="GST or tax component in INR."
    )
    total_amount: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Total legal invoice value in INR (subtotal + tax_amount)."
    )
    document_uri: Optional[str] = Field(
        None,
        description="Location URI of generated or scanned invoice PDF."
    )


class BankTransaction(ContractBaseModel):
    """
    Normalized bank statement or UPI statement line credit.
    """
    transaction_id: str = Field(
        default_factory=generate_uuid,
        description="Stable internal identifier for the banking credit."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier linking transaction to the bank statement envelope."
    )
    transaction_date: date = Field(
        ...,
        description="Posting date of the transaction on bank statement (YYYY-MM-DD)."
    )
    transaction_type: str = Field(
        ...,
        description="Electronic transfer mode (e.g. 'UPI_CR', 'IMPS', 'NEFT', 'RTGS')."
    )
    amount: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Credit amount deposited in INR (strictly Decimal)."
    )
    utr_reference: str = Field(
        ...,
        description="Unique Transaction Reference (UTR) or banking reference string."
    )
    sender_name: Optional[str] = Field(
        None,
        description="Remitter account or name extracted from bank narration."
    )
    sender_upi_id: Optional[str] = Field(
        None,
        description="Sender Virtual Payment Address (VPA) if present in narration."
    )
    raw_narration: str = Field(
        ...,
        description="Unedited, verbatim bank narration string from statement."
    )
    matched_order_id: Optional[str] = Field(
        None,
        description="Foreign reference to OrderRecord if matched during reconciliation."
    )
    payment_status: PaymentStatus = Field(
        default=PaymentStatus.UNMATCHED_CREDIT,
        description="Reconciliation status of this bank credit relative to orders."
    )


class PaymentRecord(ContractBaseModel):
    """
    Domain payment ledger entity representing an individual payment obligation state.
    """
    payment_id: str = Field(
        default_factory=generate_uuid,
        description="Stable internal identifier for the payment."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier for the reconciliation operation."
    )
    order_id: Optional[str] = Field(
        None,
        description="Linked OrderRecord identifier."
    )
    bank_transaction_id: Optional[str] = Field(
        None,
        description="Linked BankTransaction identifier."
    )
    expected_amount: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Expected order balance amount in INR."
    )
    paid_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Actual verified amount received via bank credit in INR."
    )
    shortfall_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Uncollected balance shortfall in INR (max(0, expected - paid))."
    )
    status: PaymentStatus = Field(
        ...,
        description="Categorical payment reconciliation status."
    )
    reconciled_at: Optional[datetime] = Field(
        None,
        description="UTC ISO 8601 timestamp when deterministic reconciliation matched the record."
    )


class SettlementLine(ContractBaseModel):
    """
    Itemized deduction line item from a marketplace remittance report (e.g. Meesho, Amazon).
    """
    line_id: str = Field(
        default_factory=generate_uuid,
        description="Stable internal UUID for the settlement line item."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier linking this line to the settlement report ingestion."
    )
    settlement_id: str = Field(
        ...,
        description="Marketplace settlement report batch identifier (e.g. 'MEESHO-SETTLE-OCT2024')."
    )
    marketplace: str = Field(
        ...,
        description="Marketplace platform name (e.g. 'Meesho', 'Amazon')."
    )
    order_reference: str = Field(
        ...,
        description="Marketplace internal order identifier."
    )
    gross_amount: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Gross order value before deductions in INR."
    )
    commission_fee: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Marketplace platform commission deducted in INR."
    )
    shipping_fee: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Forward logistics and courier charges deducted in INR."
    )
    return_fee: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Return to Origin (RTO) or reverse logistics charges deducted in INR."
    )
    tax_deduction: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Statutory Tax Collected at Source (TCS) and TDS deducted in INR."
    )
    other_known_adjustment: Decimal = Field(
        default=Decimal("0.00"),
        description="Itemized adjustments (packaging, penalties) in INR."
    )
    net_amount: Decimal = Field(
        ...,
        description="Net payable amount for this line item in INR."
    )
    matched_order_id: Optional[str] = Field(
        None,
        description="Linked seller OrderRecord identifier if matched."
    )


class DeliveryRecord(ContractBaseModel):
    """
    Physical shipment tracking and carrier fulfillment record.
    """
    delivery_id: str = Field(
        default_factory=generate_uuid,
        description="Stable internal delivery tracking identifier."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier linking delivery record to fulfillment run."
    )
    order_id: str = Field(
        ...,
        description="Linked OrderRecord identifier."
    )
    carrier: str = Field(
        ...,
        description="Logistics provider name (e.g. 'Delhivery Express', 'BlueDart', 'DTDC')."
    )
    tracking_number: str = Field(
        ...,
        description="Airway Bill (AWB) or courier tracking number."
    )
    dispatch_date: date = Field(
        ...,
        description="Date parcel was handed to courier (YYYY-MM-DD)."
    )
    promised_delivery_date: Optional[date] = Field(
        None,
        description="Target delivery date promised to customer."
    )
    actual_delivery_date: Optional[date] = Field(
        None,
        description="Confirmed delivery date from courier tracking."
    )
    is_delayed: bool = Field(
        default=False,
        description="Flag indicating delivery occurred after promised_delivery_date."
    )
    proof_of_delivery_uri: Optional[str] = Field(
        None,
        description="URI or signature proof reference from courier."
    )


class PromiseRecord(ContractBaseModel):
    """
    Structured commitment extracted from conversational text.
    Confidence score is purely statistical metadata and NEVER treated as proof.
    """
    promise_id: str = Field(
        default_factory=generate_uuid,
        description="Stable internal unique identifier for the extracted promise."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier linking promise extraction to source communication."
    )
    customer_id: str = Field(
        ...,
        description="Linked customer profile identifier."
    )
    order_id: Optional[str] = Field(
        None,
        description="Linked order identifier if referenced in conversation."
    )
    channel: str = Field(
        default="WhatsApp",
        description="Source communication channel."
    )
    speaker: str = Field(
        ...,
        description="'SELLER' or 'CUSTOMER'."
    )
    promise_type: PromiseType = Field(
        ...,
        description="Category of commitment."
    )
    promise_details: str = Field(
        ...,
        description="Structured summary of the commitment made."
    )
    target_date: Optional[date] = Field(
        None,
        description="Target fulfillment date if explicitly stated (YYYY-MM-DD)."
    )
    status: PromiseStatus = Field(
        default=PromiseStatus.PENDING,
        description="Fulfillment lifecycle status of this promise."
    )
    raw_message_snippet: str = Field(
        ...,
        description="Exact quote from customer conversation providing provenance."
    )
    confidence_score: Optional[Decimal] = Field(
        None,
        ge=Decimal("0.00"),
        le=Decimal("1.00"),
        description="Extraction certainty metadata between 0.00 and 1.00. INVARIANT: Confidence is informational only and MUST NEVER be treated as financial or legal proof."
    )
    extracted_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp when promise was extracted in UTC ISO 8601."
    )


# ---------------------------------------------------------------------------
# Case Synthesis & Evidence Models
# ---------------------------------------------------------------------------

class EvidenceItem(ContractBaseModel):
    """
    Individual verifiable evidence artifact linked to a CommercialCase.
    Must include full source provenance.
    """
    evidence_id: str = Field(
        default_factory=generate_uuid,
        description="Stable unique identifier for this evidence link."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier linking evidence to the case synthesis operation."
    )
    evidence_type: EvidenceType = Field(
        ...,
        description="Categorical type of evidence artifact."
    )
    source_table: str = Field(
        ...,
        description="Database table or storage partition where origin record resides."
    )
    source_entity_id: str = Field(
        ...,
        description="Primary key of the underlying entity."
    )
    source_file: Optional[str] = Field(
        None,
        description="Original uploaded filename providing provenance (e.g. 'bank_statement.csv')."
    )
    source_line_number: Optional[int] = Field(
        None,
        ge=1,
        description="Exact line number in origin CSV or text file if applicable."
    )
    snapshot_payload: Dict[str, Any] = Field(
        ...,
        description="Immutable JSON snapshot of the source entity at the time of linkage."
    )
    confidence: Optional[Decimal] = Field(
        Decimal("1.00"),
        ge=Decimal("0.00"),
        le=Decimal("1.00"),
        description="Linkage certainty score. 1.00 represents deterministic relational join."
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        description="Time evidence was linked to case in UTC ISO 8601."
    )


class Finding(ContractBaseModel):
    """
    Deterministic factual finding or mathematical proof establishing a discrepancy.
    """
    finding_id: str = Field(
        default_factory=generate_uuid,
        description="Stable identifier for this finding."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier linking finding to case synthesis."
    )
    finding_type: str = Field(
        ...,
        description="Categorical finding type (e.g. 'SHORTFALL_IDENTIFIED', 'UNEXPLAINED_DEDUCTION')."
    )
    proof_description: str = Field(
        ...,
        description="Human-readable step-by-step arithmetic or factual proof."
    )
    impact_amount: Decimal = Field(
        default=Decimal("0.00"),
        description="Quantified financial impact in INR (positive indicates money due to seller)."
    )
    severity: Severity = Field(
        ...,
        description="Severity classification of the finding."
    )
    evidence_ids: List[str] = Field(
        default_factory=list,
        description="List of EvidenceItem.evidence_id references substantiating this finding."
    )


class CommercialCase(ContractBaseModel):
    """
    Aggregate root representing a discrepancy case between promises, orders,
    payments, deliveries, or marketplace settlements.
    """
    case_id: str = Field(
        default_factory=generate_uuid,
        description="Globally unique stable identifier for the case."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier tracking the entire lifecycle of the case."
    )
    case_number: str = Field(
        ...,
        description="Human-readable reference number (e.g. 'CASE-2024-001')."
    )
    title: str = Field(
        ...,
        description="Concise summary title of the discrepancy."
    )
    case_type: str = Field(
        ...,
        description="Categorical type: 'PAYMENT_SHORTFALL', 'DUPLICATE_PAYMENT', 'MARKETPLACE_VARIANCE', 'BROKEN_PROMISE', 'UNRECORDED_GIFT'."
    )
    status: CaseStatus = Field(
        default=CaseStatus.NEW,
        description="Current FSM lifecycle status of the case."
    )
    severity: Severity = Field(
        ...,
        description="Severity level prioritizing operational urgency."
    )
    customer_id: Optional[str] = Field(
        None,
        description="Linked customer identifier if case is customer-specific."
    )
    order_id: Optional[str] = Field(
        None,
        description="Linked order identifier if applicable."
    )
    discrepancy_amount: Decimal = Field(
        default=Decimal("0.00"),
        description="Net quantified monetary discrepancy in INR."
    )
    headline: str = Field(
        ...,
        description="Plain-English explanation of the discrepancy for the micro-business owner."
    )
    explanation: str = Field(
        ...,
        description="Detailed context outlining verified facts and missing elements."
    )
    evidence_items: List[EvidenceItem] = Field(
        default_factory=list,
        description="Assembled evidence matrix establishing root cause."
    )
    findings: List[Finding] = Field(
        default_factory=list,
        description="Deterministic mathematical and factual proofs."
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp case was opened in UTC ISO 8601."
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp of latest case status update in UTC ISO 8601."
    )


# ---------------------------------------------------------------------------
# Action, Approval, and Policy Models
# ---------------------------------------------------------------------------

class ActionProposal(ContractBaseModel):
    """
    Remedial action prepared by Jarvis to resolve a CommercialCase.
    Staged in memory/database until seller approval.
    """
    action_id: str = Field(
        default_factory=generate_uuid,
        description="Stable unique identifier for the action proposal."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier linking action proposal to its source case."
    )
    case_id: str = Field(
        ...,
        description="Target CommercialCase identifier."
    )
    action_type: ActionType = Field(
        ...,
        description="Category of action to be executed."
    )
    target_recipient: str = Field(
        ...,
        description="Recipient destination (phone, email, or marketplace support portal)."
    )
    action_summary: str = Field(
        ...,
        description="Brief description of the action proposed."
    )
    payload: Dict[str, Any] = Field(
        ...,
        description="Strict execution parameters (e.g. amount in INR, draft email body, line items)."
    )
    requires_approval: bool = Field(
        default=True,
        description="Whether this action requires explicit human authorization before execution."
    )
    status: ActionStatus = Field(
        default=ActionStatus.PENDING,
        description="Lifecycle status of this action."
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        description="UTC ISO 8601 creation timestamp."
    )


class PolicyDecision(ContractBaseModel):
    """
    Output of Jarvis policy engine evaluating safety, compliance, and approval requirements.
    """
    decision_id: str = Field(
        default_factory=generate_uuid,
        description="Stable unique identifier for the policy evaluation record."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier linking decision to action proposal."
    )
    action_id: str = Field(
        ...,
        description="Action proposal evaluated."
    )
    is_allowed: bool = Field(
        ...,
        description="True if action conforms to platform safety invariants; False if blocked."
    )
    requires_human_approval: bool = Field(
        ...,
        description="True if action requires seller review before execution."
    )
    policy_rule_matched: str = Field(
        ...,
        description="Name of the specific compliance rule applied (e.g. 'RULE_14_MONEY_HITL_REQUIRED')."
    )
    violation_reasons: List[str] = Field(
        default_factory=list,
        description="List of blocking policy violations if is_allowed is False."
    )
    evaluated_at: datetime = Field(
        default_factory=utc_now,
        description="UTC ISO 8601 evaluation timestamp."
    )


class ApprovalRequest(ContractBaseModel):
    """
    Formal request presented to the micro-business owner to authorize or reject an action.
    """
    request_id: str = Field(
        default_factory=generate_uuid,
        description="Stable identifier for the approval request."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier linking approval request to action."
    )
    action_id: str = Field(
        ...,
        description="Foreign reference to ActionProposal.action_id."
    )
    case_id: str = Field(
        ...,
        description="Foreign reference to CommercialCase.case_id."
    )
    status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING,
        description="Current state of the approval request."
    )
    summary: str = Field(
        ...,
        description="Human-readable decision prompt presented to seller."
    )
    presented_payload: Dict[str, Any] = Field(
        ...,
        description="Sanitized preview of the action to be authorized."
    )
    requested_at: datetime = Field(
        default_factory=utc_now,
        description="UTC ISO 8601 timestamp when request was staged."
    )


class ApprovalDecision(ContractBaseModel):
    """
    Micro-business owner's explicit decision regarding an ApprovalRequest.
    """
    decision_id: str = Field(
        default_factory=generate_uuid,
        description="Stable identifier for the decision record."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier connecting decision to approval request."
    )
    request_id: str = Field(
        ...,
        description="Foreign reference to ApprovalRequest.request_id."
    )
    action_id: str = Field(
        ...,
        description="Foreign reference to ActionProposal.action_id."
    )
    case_id: str = Field(
        ...,
        description="Foreign reference to CommercialCase.case_id."
    )
    decision: ApprovalStatus = Field(
        ...,
        description="Explicit seller decision: must be 'approved' or 'rejected'."
    )
    actor: str = Field(
        default="Seller (Manual HITL)",
        description="Identity of the authorized human decision-maker."
    )
    rejection_reason: Optional[str] = Field(
        None,
        description="Seller-provided explanation if action was rejected or dismissed."
    )
    decided_at: datetime = Field(
        default_factory=utc_now,
        description="UTC ISO 8601 timestamp when decision was submitted."
    )


# ---------------------------------------------------------------------------
# Execution Results & Receipt Models
# ---------------------------------------------------------------------------

class DeliveryResult(ContractBaseModel):
    """
    Result returned by carrier gateway or simulated messaging service.
    """
    result_id: str = Field(
        default_factory=generate_uuid,
        description="Stable identifier for delivery execution response."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier for execution operation."
    )
    carrier_message_id: str = Field(
        ...,
        description="External reference identifier returned by provider or simulator."
    )
    status: str = Field(
        ...,
        description="Delivery dispatch status (e.g. 'DRAFT_CREATED', 'SIMULATED_DISPATCH')."
    )
    is_simulated: bool = Field(
        default=True,
        description="True indicates simulated sandbox delivery per safety rules; never live."
    )
    executed_at: datetime = Field(
        default_factory=utc_now,
        description="UTC ISO 8601 execution timestamp."
    )


class PaymentLinkResult(ContractBaseModel):
    """
    Result returned by Razorpay Payment Links API in Test Mode.
    """
    result_id: str = Field(
        default_factory=generate_uuid,
        description="Stable identifier for payment link execution response."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier for payment link creation."
    )
    payment_link_id: str = Field(
        ...,
        description="Provider payment link identifier (e.g. 'plink_test_8923a10df5')."
    )
    amount: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Link amount in INR (strictly Decimal)."
    )
    currency: str = Field(
        default="INR",
        description="ISO 4217 currency code."
    )
    short_url: str = Field(
        ...,
        description="Sandbox payment link URL (e.g. 'https://rzp.io/i/test_9a8df1')."
    )
    mode: str = Field(
        default="TEST_SANDBOX",
        description="Execution mode: strictly 'TEST_SANDBOX'."
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        description="UTC ISO 8601 timestamp of link creation."
    )


class ActionReceipt(ContractBaseModel):
    """
    Immutable, append-only cryptographic receipt documenting an approved or rejected action.
    Chains SHA-256 digests to guarantee tamper-evident audit trails.
    """
    receipt_id: str = Field(
        default_factory=generate_uuid,
        description="Stable unique identifier for the immutable receipt."
    )
    correlation_id: str = Field(
        ...,
        description="Trace identifier linking receipt to the initiating transaction."
    )
    approval_id: str = Field(
        ...,
        description="Foreign reference to ApprovalDecision.decision_id."
    )
    action_id: str = Field(
        ...,
        description="Foreign reference to ActionProposal.action_id."
    )
    case_id: str = Field(
        ...,
        description="Foreign reference to CommercialCase.case_id."
    )
    decision: ApprovalStatus = Field(
        ...,
        description="Human decision authorized ('approved' or 'rejected')."
    )
    actor: str = Field(
        default="Seller (Manual HITL)",
        description="Identity of the human decision-maker."
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="UTC ISO 8601 timestamp of receipt generation."
    )
    payload_snapshot: Dict[str, Any] = Field(
        ...,
        description="Masked snapshot of the authorized action payload."
    )
    execution_result: Dict[str, Any] = Field(
        ...,
        description="Full response from the sandbox gateway or simulator."
    )
    receipt_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 cryptographic digest of canonical fields."
    )
    tamper_chain_previous_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 hash of the immediately preceding receipt in the ledger."
    )


# ---------------------------------------------------------------------------
# API Transport & Envelope Models
# ---------------------------------------------------------------------------

class RunResponse(ContractBaseModel):
    """
    Standard API response envelope returned after executing reconciliation,
    ingestion, or action execution workflows.
    """
    correlation_id: str = Field(
        ...,
        description="Trace identifier for the completed workflow."
    )
    status: str = Field(
        ...,
        description="Execution status ('SUCCESS', 'PARTIAL_SUCCESS', 'ERROR')."
    )
    summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metrics summary (e.g. orders_matched, shortfalls_found, cases_opened)."
    )
    cases_created: List[str] = Field(
        default_factory=list,
        description="List of CommercialCase.case_id identifiers generated or updated."
    )
    receipts_issued: List[str] = Field(
        default_factory=list,
        description="List of ActionReceipt.receipt_id identifiers generated during the run."
    )
    completed_at: datetime = Field(
        default_factory=utc_now,
        description="UTC ISO 8601 completion timestamp."
    )
    watermark: str = Field(
        default="Synthetic demo dataset modelled on a small online seller’s workflow.",
        description="Notice classifying data as synthetic demo records."
    )


class ErrorResponse(ContractBaseModel):
    """
    Standard structured error payload returned when a contract invariant,
    parsing operation, or safety rule fails.
    """
    correlation_id: str = Field(
        ...,
        description="Trace identifier for correlation and debugging."
    )
    error_code: ErrorCode = Field(
        ...,
        description="Standardized machine-readable error code."
    )
    message: str = Field(
        ...,
        description="Human-readable explanation of the error."
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="Time the error occurred in UTC ISO 8601."
    )
    details: List[ErrorDetail] = Field(
        default_factory=list,
        description="Field-level error details or contextual breakdown."
    )
