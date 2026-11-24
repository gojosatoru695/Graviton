from enum import Enum


class CaseStatus(str, Enum):
    """
    Lifecycle states for a commercial discrepancy Case.
    """
    NEW = "new"
    INVESTIGATING = "investigating"
    NEEDS_APPROVAL = "needs_approval"
    ACTION_PREPARED = "action_prepared"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESOLVED = "resolved"
    BLOCKED = "blocked"


class PaymentStatus(str, Enum):
    """
    Reconciliation state of customer payment relative to order obligations.
    """
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    UNPAID = "unpaid"
    DUPLICATE_CANDIDATE = "duplicate_candidate"
    REFUND_MATCH = "refund_match"
    UNMATCHED_CREDIT = "unmatched_credit"


class SettlementVarianceStatus(str, Enum):
    """
    Classification of marketplace settlement remittance variance.
    """
    FULLY_EXPLAINED = "fully_explained"
    PARTIALLY_EXPLAINED = "partially_explained"
    UNEXPLAINED_RESIDUAL = "unexplained_residual"
    INSUFFICIENT_DATA = "insufficient_data"


class PromiseType(str, Enum):
    """
    Category of explicit commitment extracted from communications.
    """
    DELIVERY_DATE = "delivery_date"
    FREE_GIFT = "free_gift"
    DISCOUNT = "discount"
    CUSTOMIZATION = "customization"
    PAYMENT_COMMITMENT = "payment_commitment"


class PromiseStatus(str, Enum):
    """
    Fulfillment status of an extracted promise.
    """
    PENDING = "pending"
    KEPT = "kept"
    BROKEN = "broken"
    UNRECORDED = "unrecorded"


class ActionType(str, Enum):
    """
    Type of executable remedial action prepared by Jarvis.
    """
    RAZORPAY_PAYMENT_LINK = "razorpay_payment_link"
    GMAIL_DRAFT = "gmail_draft"
    SEND_EMAIL = "send_email"
    SEND_CUSTOMER_MESSAGE = "send_customer_message"
    SETTLEMENT_DISPUTE_PACK = "settlement_dispute_pack"


class ActionStatus(str, Enum):
    """
    Execution lifecycle status of an ActionProposal.
    """
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class ApprovalStatus(str, Enum):
    """
    State of an approval request submitted to the micro-business owner.
    """
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class EvidenceType(str, Enum):
    """
    Categorization of factual evidence artifacts linked to a Case.
    """
    ORDER = "order"
    BANK_TXN = "bank_txn"
    PROMISE = "promise"
    INVOICE = "invoice"
    SETTLEMENT_LINE = "settlement_line"
    DELIVERY_RECORD = "delivery_record"
    CHAT_SNIPPET = "chat_snippet"


class Severity(str, Enum):
    """
    Operational and financial impact severity rating.
    """
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
